#!/usr/bin/env python3
"""Conan recipe for Apollo Rover v0.40.0 — Rust/Cargo project.

Rover is a CLI tool for working with the Apollo GraphQL Registry.
Build system: Cargo (Rust).

Key adaptations for OHOS:
  - Switched crypto provider from aws-lc-rs to ring (aws-lc-sys assembly
    generation fails on OHOS due to missing Perl/Go integration in cmake)
  - All reqwest features changed from "rustls" to "rustls-no-provider"
  - Added explicit rustls/hyper-rustls/tokio-rustls deps with "ring" feature
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, unzip, export_conandata_patches, apply_conandata_patches


class RoverConan(ConanFile):
    name = "rover"
    version = "latest"
    description = "Apollo Rover - CLI tool for working with the Apollo GraphQL Registry"
    license = "MIT"
    homepage = "https://github.com/apollographql/rover"
    url = "https://github.com/apollographql/rover"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rover {self.version} is only supported on Linux/OHOS, "
                f"not {self.settings.os}"
            )

    def requirements(self):
        pass

    def build_requirements(self):
        pass

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # Fallback 1: curl -k for OHOS where Python SSL module is unavailable
            import hashlib
            filename = os.path.basename(url)
            try:
                self.run(f'curl -kL -o "{filename}" "{url}"', cwd=self.source_folder)
                filepath = os.path.join(self.source_folder, filename)
                with open(filepath, "rb") as f:
                    actual_sha = hashlib.sha256(f.read()).hexdigest()
                if actual_sha != sha256:
                    raise ConanInvalidConfiguration(
                        f"SHA256 mismatch: expected {sha256}, got {actual_sha}"
                    )
                unzip(self, filename, destination=self.source_folder, strip_root=True)
            except Exception:
                # Fallback 2: local tarball (GitHub unreachable in CI)
                local_tarball = os.path.expanduser("~/tmp/builds/rover-latest.tar.gz")
                if not os.path.exists(local_tarball):
                    local_tarball = os.path.join(
                        os.environ.get("TMPDIR", os.path.expanduser("~/tmp")),
                        "builds", "rover-latest.tar.gz"
                    )
                if os.path.exists(local_tarball):
                    self.output.info(f"Using local tarball: {local_tarball}")
                    with open(local_tarball, "rb") as f:
                        actual_sha = hashlib.sha256(f.read()).hexdigest()
                    if actual_sha != sha256:
                        raise ConanInvalidConfiguration(
                            f"Local tarball SHA256 mismatch: expected {sha256}, got {actual_sha}"
                        )
                    unzip(self, local_tarball, destination=self.source_folder, strip_root=True)
                else:
                    raise

    def _ensure_cargo(self):
        """Detect or install Rust toolchain via harmonybrew."""
        home = os.path.expanduser("~")
        cert_pem = os.path.join(home, "usr", "local", "ssl", "cert.pem")
        if os.path.exists(cert_pem):
            os.environ["SSL_CERT_FILE"] = cert_pem
            os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

        # Configure crates.io mirror
        self._setup_cargo_mirror(home)

        if shutil.which("cargo"):
            return

        # 1. Check existing harmonybrew cargo
        harmonybrew_bin = os.path.join(home, ".harmonybrew", "bin")
        harmonybrew_cargo = os.path.join(harmonybrew_bin, "cargo")
        if os.path.isfile(harmonybrew_cargo) and os.access(harmonybrew_cargo, os.X_OK):
            self._add_path(harmonybrew_bin)
            return

        # 2. Check existing ~/.cargo/bin
        cargo_bin_dir = os.path.join(home, ".cargo", "bin")
        cargo_bin = os.path.join(cargo_bin_dir, "cargo")
        if os.path.isfile(cargo_bin) and os.access(cargo_bin, os.X_OK):
            self._add_path(cargo_bin_dir)
            return

        # 3. Ensure harmonybrew is available
        brew_bin = os.path.join(harmonybrew_bin, "brew")
        if not shutil.which("brew"):
            if os.path.isfile(brew_bin):
                self.output.info("Found harmonybrew, adding to PATH")
                self._add_path(harmonybrew_bin)
            else:
                self.output.info("Installing harmonybrew...")
                harmonybrew_repo = os.path.join(home, ".harmonybrew", "Homebrew")
                if not os.path.isdir(harmonybrew_repo):
                    if os.path.exists(cert_pem):
                        os.environ["GIT_SSL_CAINFO"] = cert_pem
                    self.run(
                        f'git clone --depth=1 https://atomgit.com/Harmonybrew/brew.git {harmonybrew_repo}'
                    )
                os.makedirs(harmonybrew_bin, exist_ok=True)
                self.run(f'ln -sf {harmonybrew_repo}/bin/brew {brew_bin}')
                self._add_path(harmonybrew_bin)

        # 4. Install Rust via harmonybrew
        self.output.info("Installing Rust via harmonybrew...")
        self.run("brew install rust")

        if shutil.which("cargo"):
            return
        if os.path.isfile(harmonybrew_cargo) and os.access(harmonybrew_cargo, os.X_OK):
            self._add_path(harmonybrew_bin)
            return

        raise Exception("Rust installation failed — cargo still not found after brew install rust")

    def _add_path(self, p):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

    def _setup_cargo_mirror(self, home):
        """Configure crates.io mirror for fast downloads in China."""
        cargo_dir = os.path.join(home, ".cargo")
        config_path = os.path.join(cargo_dir, "config.toml")
        if os.path.isfile(config_path):
            return
        os.makedirs(cargo_dir, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(
                '[source.crates-io]\n'
                'replace-with = "ustc"\n'
                '\n'
                '[source.ustc]\n'
                'registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"\n'
                '\n'
                '[net]\n'
                'git-fetch-with-cli = true\n'
                '\n'
                '[http]\n'
                'multiplexing = false\n'
            )
        self.output.info("Configured USTC crates.io mirror")

    def _ensure_cc(self):
        """Ensure a C compiler/linker (`cc`) is available in PATH.

        rustc looks for `cc` in PATH to link build script binaries.
        """
        if shutil.which("cc"):
            return

        clang_path = self._find_clang()
        if not clang_path and shutil.which("brew"):
            self.output.info("Installing ohos-sdk + llvm-gcc-compat via harmonybrew...")
            self.run("brew install ohos-sdk")
            self.run("brew install llvm-gcc-compat")
            # Ensure harmonybrew bin is in PATH
            home = os.path.expanduser("~")
            harmonybrew_bin = os.path.join(home, ".harmonybrew", "bin")
            if harmonybrew_bin not in os.environ.get("PATH", ""):
                os.environ["PATH"] = harmonybrew_bin + os.pathsep + os.environ.get("PATH", "")
            clang_path = self._find_clang()

        if clang_path:
            os.environ["CC"] = clang_path
            os.environ["CXX"] = clang_path.replace("clang", "clang++")
            self.output.info(f"CC={clang_path}")
            cc_bindir = os.path.join(self.source_folder, "._cc_bin")
            os.makedirs(cc_bindir, exist_ok=True)
            cc_link = os.path.join(cc_bindir, "cc")
            if not os.path.exists(cc_link):
                os.symlink(clang_path, cc_link)
            os.environ["PATH"] = cc_bindir + os.pathsep + os.environ.get("PATH", "")
            self.output.info(f"Created cc symlink → {clang_path} in {cc_bindir}")
        else:
            self.output.warning("No C compiler found; build may fail")

    def _find_clang(self):
        """Locate clang binary on the system. Returns path or None."""
        clang = shutil.which("clang")
        if clang:
            return clang
        home = os.path.expanduser("~")
        import glob
        for cellar in glob.glob(os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk", "*", "native", "llvm")):
            candidate = os.path.join(cellar, "bin", "clang")
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        candidate = os.path.join(home, ".harmonybrew", "bin", "clang")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        return None

    def _fix_libstdcxx(self):
        """Redirect -lstdc++ → -lc++_shared in rustc sysroot target lib dir.

        rustc adds `-lstdc++` to every linker invocation, but OHOS uses libc++
        (LLVM) instead of libstdc++ (GCC). Creates a linker script in the
        rustc target lib directory, which is already in the linker's default -L
        search path, so no extra RUSTFLAGS are needed.
        """
        import subprocess
        rustc = shutil.which("rustc")
        if not rustc:
            self.output.warning("rustc not found in PATH; -lstdc++ fix skipped")
            return
        try:
            result = subprocess.run([rustc, "--print", "sysroot"],
                                    capture_output=True, text=True, check=True)
            sysroot = result.stdout.strip()
        except Exception as e:
            self.output.warning(f"Cannot determine rustc sysroot: {e}")
            return

        target = "aarch64-unknown-linux-ohos"
        lib_dir = os.path.join(sysroot, "lib", "rustlib", target, "lib")
        if not os.path.isdir(lib_dir):
            self.output.warning(f"rustc target lib dir not found: {lib_dir}")
            return

        libstdcxx_so = os.path.join(lib_dir, "libstdc++.so")
        if not os.path.exists(libstdcxx_so):
            with open(libstdcxx_so, "w") as f:
                f.write("INPUT(-lc++_shared)\n")
            self.output.info(f"Created {libstdcxx_so}")
        libstdcxx_a = os.path.join(lib_dir, "libstdc++.a")
        if not os.path.exists(libstdcxx_a):
            with open(libstdcxx_a, "w") as f:
                f.write("INPUT(-lc++_static -lc++abi)\n")
            self.output.info(f"Created {libstdcxx_a}")

    def build(self):
        apply_conandata_patches(self)
        # Step 1: Ensure Rust toolchain
        self._ensure_cargo()
        # Step 2: Ensure C compiler (cc) is in PATH
        self._ensure_cc()
        # Step 3: Fix -lstdc++ → -lc++_shared
        self._fix_libstdcxx()

        # E002: OHOS /tmp is read-only, use $HOME/tmp
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # SSL cert for https downloads
        cert_pem = os.path.expanduser("~/usr/local/ssl/cert.pem")
        if os.path.exists(cert_pem):
            os.environ["SSL_CERT_FILE"] = cert_pem
            os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

        # Set environment variables for cargo build
        old_env = {}
        env_vars = {
            "CARGO_HOME": os.path.join(self.build_folder, ".cargo-home"),
            "CARGO_NET_GIT_FETCH_WITH_CLI": "true",
            "CARGO_TERM_PROGRESS_WHEN": "always",
            "CARGO_TERM_PROGRESS_WIDTH": "80",
            "TMPDIR": tmpdir,
            "TEMP": tmpdir,
            "TMP": tmpdir,
        }

        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            self.run("cargo build --release -j2", cwd=self.source_folder)
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def package(self):
        bin_dir = os.path.join(self.source_folder, "target", "release")
        copy(
            self,
            "rover",
            src=bin_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.builddirs = []
        self.cpp_info.bindirs = ["bin"]
