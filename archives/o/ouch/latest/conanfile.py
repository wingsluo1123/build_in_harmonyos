#!/usr/bin/env python3
"""Conan recipe — ouch (Rust/Cargo project).

ouch is a command-line utility for easily compressing and decompressing
files and directories. Built with Rust/Cargo.

Build system: Cargo (cargo build --release)
Platform: OHOS (aarch64-unknown-linux-ohos)
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class OuchConan(ConanFile):
    name = "ouch"
    version = "latest"
    description = "A command-line utility for easily compressing and decompressing files and directories."
    license = "MIT"
    homepage = "https://github.com/ouch-org/ouch"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # ouch uses Cargo for dependency management; no Conan-level dependencies
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Not applicable — ouch is a standalone binary, not a system same-name library
        pass

    def build(self):
        apply_conandata_patches(self)
        # Ensure Rust toolchain is available (CI may not have cargo pre-installed)
        self._ensure_cargo()
        # Set up environment for cargo build on OHOS
        ohos_sdk_lib = self._find_ohos_lib_dir()
        if ohos_sdk_lib:
            self._setup_libstdcxx(ohos_sdk_lib)

        rustflags = []
        if ohos_sdk_lib:
            rustflags.append(f"-L {ohos_sdk_lib}")
            rustflags.append(f"-C link-arg=-L{ohos_sdk_lib}")
        os.environ["RUSTFLAGS"] = " ".join(rustflags)

        cert_pem = os.path.expanduser("~/usr/local/ssl/cert.pem")
        if os.path.exists(cert_pem):
            os.environ["SSL_CERT_FILE"] = cert_pem
            os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

        # Show progress so CI doesn't timeout on no-output
        os.environ["CARGO_TERM_PROGRESS_WHEN"] = "always"
        os.environ["CARGO_TERM_PROGRESS_PLAIN"] = "true"
        self.run("cargo build --release", cwd=self.source_folder)

    def package(self):
        binary_path = os.path.join(self.source_folder, "target", "release", "ouch")
        if os.path.exists(binary_path):
            copy(self, "ouch", src=os.path.dirname(binary_path), dst=os.path.join(self.package_folder, "bin"))
        else:
            raise Exception(f"Built binary not found at {binary_path}")

    def package_info(self):
        # ouch is a standalone CLI binary; make bin/ available in PATH
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    def _ensure_cargo(self):
        """Detect or install Rust toolchain via harmonybrew.

        CI may not have cargo pre-installed. rustup doesn't support HarmonyOS,
        and pre-built gnu tarballs need /lib/ld-linux-aarch64.so.1 (absent on OHOS).
        The correct approach is harmonybrew, which provides OHOS-compiled Rust
        (aarch64-unknown-linux-ohos target, musl-linked).
        """
        home = os.path.expanduser("~")
        cert_pem = os.path.join(home, "usr", "local", "ssl", "cert.pem")
        if os.path.exists(cert_pem):
            os.environ["SSL_CERT_FILE"] = cert_pem
            os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

        def _add_path(p):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

        # Always ensure crates.io mirror is configured (fast downloads in China)
        self._setup_cargo_mirror(home)

        if shutil.which("cargo"):
            return

        # 1. Check existing harmonybrew cargo
        harmonybrew_bin = os.path.join(home, ".harmonybrew", "bin")
        harmonybrew_cargo = os.path.join(harmonybrew_bin, "cargo")
        if os.path.isfile(harmonybrew_cargo) and os.access(harmonybrew_cargo, os.X_OK):
            _add_path(harmonybrew_bin)
            return

        # 2. Check existing ~/.cargo/bin
        cargo_bin_dir = os.path.join(home, ".cargo", "bin")
        cargo_bin = os.path.join(cargo_bin_dir, "cargo")
        if os.path.isfile(cargo_bin) and os.access(cargo_bin, os.X_OK):
            _add_path(cargo_bin_dir)
            return

        # 3. Ensure harmonybrew is available
        brew_bin = os.path.join(harmonybrew_bin, "brew")
        if not shutil.which("brew"):
            if os.path.isfile(brew_bin):
                self.output.info("Found harmonybrew, adding to PATH")
                _add_path(harmonybrew_bin)
            else:
                self.output.info("Installing harmonybrew...")
                harmonybrew_repo = os.path.join(home, ".harmonybrew", "Homebrew")
                if not os.path.isdir(harmonybrew_repo):
                    # SSL workaround for git clone on OHOS
                    if os.path.exists(cert_pem):
                        os.environ["GIT_SSL_CAINFO"] = cert_pem
                    self.run(
                        f'git clone --depth=1 https://atomgit.com/Harmonybrew/brew.git {harmonybrew_repo}'
                    )
                os.makedirs(harmonybrew_bin, exist_ok=True)
                self.run(f'ln -sf {harmonybrew_repo}/bin/brew {brew_bin}')
                _add_path(harmonybrew_bin)

        # 4. Install Rust via harmonybrew
        self.output.info("Installing Rust via harmonybrew...")
        self.run("brew install rust")

        if shutil.which("cargo"):
            return
        if os.path.isfile(harmonybrew_cargo) and os.access(harmonybrew_cargo, os.X_OK):
            _add_path(harmonybrew_bin)
            return

        raise Exception("Rust installation failed — cargo still not found after brew install rust")

    def _setup_cargo_mirror(self, home):
        """Configure crates.io mirror for fast downloads in China."""
        cargo_dir = os.path.join(home, ".cargo")
        config_path = os.path.join(cargo_dir, "config.toml")
        if os.path.isfile(config_path):
            return  # already configured
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

    def _find_ohos_lib_dir(self):
        """Find the OHOS SDK C++ library directory."""
        import glob
        candidates = [
            os.path.expanduser("~/.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib/aarch64-linux-ohos"),
            os.path.expanduser("~/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib/aarch64-linux-ohos"),
        ]
        for pattern in candidates:
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    return path
        try:
            import subprocess
            result = subprocess.run(["rustc", "--print", "sysroot"], capture_output=True, text=True)
            sysroot = result.stdout.strip()
            p = Path(sysroot)
            while p.parent != p:
                lib_dir = p / "lib" / "aarch64-linux-ohos"
                if lib_dir.is_dir():
                    return str(lib_dir)
                p = p.parent
        except Exception:
            pass
        return None

    def _setup_libstdcxx(self, lib_dir):
        """Create libstdc++ linker scripts pointing to libc++ (E050 workaround)."""
        libstdcxx_so = os.path.join(lib_dir, "libstdc++.so")
        libstdcxx_a = os.path.join(lib_dir, "libstdc++.a")
        if not os.path.exists(libstdcxx_so):
            with open(libstdcxx_so, "w") as f:
                f.write("INPUT(-lc++_shared)\n")
        if not os.path.exists(libstdcxx_a):
            with open(libstdcxx_a, "w") as f:
                f.write("INPUT(-lc++_static -lc++abi)\n")
