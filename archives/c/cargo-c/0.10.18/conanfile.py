#!/usr/bin/env python3
"""Conan recipe — cargo-c 0.10.18 (cargo build system).

cargo-c is a Rust cargo subcommand that builds and installs C-compatible
libraries from Rust crates. It produces 4 binaries: cargo-capi, cargo-cbuild,
cargo-cinstall, cargo-ctest.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CargoCConan(ConanFile):
    name = "cargo-c"
    version = "0.10.18"
    description = "Helper program to build and install c-like libraries from Rust crates"
    license = "MIT"
    homepage = "https://github.com/lu-zero/cargo-c"
    url = "https://github.com/lu-zero/cargo-c"
    topics = ("cargo", "cdylib", "rust", "c-api")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # cargo-c dynamically links against OpenSSL for TLS support.
        # OpenSSL is resolved via PKG_CONFIG_PATH / OPENSSL_DIR env vars
        # set in build(), not as a Conan-managed package, because the
        # Rust build system (cargo) manages its own dependency resolution
        # and uses pkg-config to find system libraries.
        pass

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Ensure Rust toolchain is available.
        # On HarmonyOS, Rust is installed via Harmonybrew (community package manager).
        cargo_bin = shutil.which("cargo")
        if not cargo_bin:
            # Try installing Rust via cmd-pkgs (fast, pre-built HNP package)
            self.run(
                'curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh '
                '| sh -s -- rust 1.97.1 2>&1 || true'
            )
            cargo_bin = shutil.which("cargo")

        if not cargo_bin:
            # Fallback: install via Harmonybrew (community Homebrew for HarmonyOS)
            brew_bin = "/storage/Users/currentUser/.harmonybrew/bin"
            brew_shellenv = os.path.join(brew_bin, "brew")
            if not os.path.isfile(brew_shellenv):
                # Install harmonybrew first
                self.run(
                    'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)" 2>&1 || true'
                )
            if os.path.isfile(brew_shellenv):
                self.run(
                    f'eval "$({brew_shellenv} shellenv)" && brew install rust 2>&1 || true'
                )
            cargo_bin = shutil.which("cargo") or os.path.join(brew_bin, "cargo")

        if not os.path.isfile(cargo_bin):
            raise Exception("Rust toolchain (cargo) not available and installation failed. "
                             "Please install Rust on the build machine.")

        # Resolve C/C++ compiler from Conan settings or system PATH.
        # Rust build scripts invoke cc/clang for C compilation of native deps.
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "clang++")
        if not shutil.which(cc):
            cc = shutil.which("clang") or "clang"
        if not shutil.which(cxx):
            cxx = shutil.which("clang++") or "clang++"

        # Resolve OpenSSL — check common HarmonyOS install locations.
        openssl_dir = os.environ.get("OPENSSL_DIR", "")
        if not openssl_dir:
            for candidate in (
                os.path.expanduser("~/.harmonybrew/opt/openssl@3"),
                "/storage/Users/currentUser/.harmonybrew/opt/openssl@3",
            ):
                if os.path.isdir(candidate):
                    openssl_dir = candidate
                    break
        openssl_libdir = os.path.join(openssl_dir, "lib") if openssl_dir else ""
        openssl_incdir = os.path.join(openssl_dir, "include") if openssl_dir else ""

        # Set build environment for cargo.
        # These are standard environment variables recognized by cargo/rustc
        # and the cc crate (Rust's C compilation helper).
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        # Ensure cargo can find rustc and other Rust tools in PATH.
        cargo_dir = os.path.dirname(cargo_bin)
        os.environ["PATH"] = cargo_dir + os.pathsep + os.environ.get("PATH", "")
        # Set RPATH at link time so binaries find bundled shared libraries
        # at runtime (bin/ -> ../lib/). Using $ORIGIN for portability.
        # This avoids post-build patchelf which would invalidate ELF codesign.
        os.environ["RUSTFLAGS"] = (
            f"-C linker={cc} -C link-arg=-Wl,-rpath,\\$ORIGIN/../lib"
        )
        if openssl_dir:
            os.environ["OPENSSL_DIR"] = openssl_dir
            os.environ["OPENSSL_LIB_DIR"] = openssl_libdir
            os.environ["OPENSSL_INCLUDE_DIR"] = openssl_incdir
            os.environ["PKG_CONFIG_PATH"] = openssl_libdir + "/pkgconfig"

        self.run(f'"{cargo_bin}" build --release', cwd=self.source_folder)

    def package(self):
        build_out = os.path.join(self.source_folder, "target", "release")
        for binary in ("cargo-capi", "cargo-cbuild", "cargo-cinstall", "cargo-ctest"):
            copy(self, binary, src=build_out, dst=os.path.join(self.package_folder, "bin"))

        # Copy required shared libraries (libssl.so.3, libcrypto.so.3).
        # These are not in the system library path and must be bundled.
        openssl_libdir = ""
        for candidate in (
            os.path.expanduser("~/.harmonybrew/opt/openssl@3/lib"),
            "/storage/Users/currentUser/.harmonybrew/opt/openssl@3/lib",
            "/storage/Users/currentUser/.harmonybrew/lib",
            "/data/service/hnp/OpenHarmonyPCDeveloper_build_in_harmonyos_ai_worker.org/OpenHarmonyPCDeveloper_build_in_harmonyos_ai_worker_1.0.0/lib/external",
        ):
            if os.path.isfile(os.path.join(candidate, "libssl.so.3")):
                openssl_libdir = candidate
                break
        if openssl_libdir:
            for lib in ("libssl.so.3", "libcrypto.so.3"):
                copy(self, lib, src=openssl_libdir, dst=os.path.join(self.package_folder, "lib"))

        # ELF signing (required on HarmonyOS for binary execution).
        # The OHOS SDK keystore uses a well-known default password "123456"
        # which is shipped with the public SDK, not a production secret.
        # Signing is non-blocking: binaries may already have a codesign
        # section from the linker, in which case re-signing is skipped.
        sign_tool = shutil.which("binary-sign-tool")
        if sign_tool:
            keystore_pwd = os.environ.get("OHOS_SIGNING_PWD", "123456")
            keystore = os.environ.get(
                "OHOS_SIGNING_KEYSTORE",
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/toolchains/lib/OpenHarmony.p12",
            )
            if os.path.isfile(keystore):
                for binary in ("cargo-capi", "cargo-cbuild", "cargo-cinstall", "cargo-ctest"):
                    bin_path = os.path.join(self.package_folder, "bin", binary)
                    if os.path.isfile(bin_path):
                        self.run(
                            f'"{sign_tool}" sign -selfSign 1 '
                            f'-keyAlias "OpenHarmony Application Certificate" '
                            f'-keystoreFile "{keystore}" '
                            f'-keystorePwd "{keystore_pwd}" '
                            f'-inFile "{bin_path}" -outFile "{bin_path}" '
                            f'|| true'
                        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
