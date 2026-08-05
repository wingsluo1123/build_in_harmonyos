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

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Ensure Rust toolchain is available
        cargo_bin = shutil.which("cargo")
        brew_bin = "/storage/Users/currentUser/.harmonybrew/bin"
        brew_shellenv = os.path.join(brew_bin, "brew")
        if not cargo_bin:
            if os.path.isfile(brew_shellenv):
                self.run(f'eval "$({brew_shellenv} shellenv)" && brew install rust 2>&1 || true')
            cargo_bin = os.path.join(brew_bin, "cargo")
            if not os.path.isfile(cargo_bin):
                cargo_bin = shutil.which("cargo") or "cargo"

        # Set up OpenSSL environment (from harmonybrew or system)
        openssl_dir = os.environ.get("OPENSSL_DIR", "")
        if not openssl_dir:
            candidate = "/storage/Users/currentUser/.harmonybrew/opt/openssl@3"
            if os.path.isdir(candidate):
                openssl_dir = candidate
        openssl_libdir = os.path.join(openssl_dir, "lib") if openssl_dir else ""
        openssl_incdir = os.path.join(openssl_dir, "include") if openssl_dir else ""

        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp")
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"
        os.environ["PATH"] = brew_bin + os.pathsep + os.environ.get("PATH", "")
        # Set linker to clang and RPATH at link time (avoids patchelf which invalidates codesign)
        os.environ["RUSTFLAGS"] = "-C linker=clang -C link-arg=-Wl,-rpath,\\$ORIGIN/../lib"
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

        # Copy required shared libraries (libssl.so.3, libcrypto.so.3)
        openssl_libdir = ""
        for candidate in (
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

        # RPATH is set at link time via RUSTFLAGS, no patchelf needed
        # ELF signing (non-blocking: binary may already have codesign from linker)
        sign_tool = shutil.which("binary-sign-tool")
        if sign_tool:
            keystore = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/toolchains/lib/OpenHarmony.p12"
            for binary in ("cargo-capi", "cargo-cbuild", "cargo-cinstall", "cargo-ctest"):
                bin_path = os.path.join(self.package_folder, "bin", binary)
                if os.path.isfile(bin_path):
                    self.run(
                        f'"{sign_tool}" sign -selfSign 1 '
                        f'-keyAlias "OpenHarmony Application Certificate" '
                        f'-keystoreFile "{keystore}" '
                        f'-keystorePwd "123456" '
                        f'-inFile "{bin_path}" -outFile "{bin_path}" '
                        f'|| true'
                    )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
