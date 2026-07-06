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
        # Ensure C compiler/linker (`cc`) is available in PATH
        self._ensure_cc()
        # Fix -lstdc++ → -lc++_shared: write linker script into rustc target lib dir
        self._fix_libstdcxx()

        cert_pem = os.path.expanduser("~/usr/local/ssl/cert.pem")
        if os.path.exists(cert_pem):
            os.environ["SSL_CERT_FILE"] = cert_pem
            os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

        # Show progress so CI doesn't timeout on no-output
        os.environ["CARGO_TERM_PROGRESS_WHEN"] = "always"
        os.environ["CARGO_TERM_PROGRESS_WIDTH"] = "80"
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

    def _ensure_cc(self):
        """Ensure a C compiler/linker (`cc`) is available in PATH.

        `rustc` looks for `cc` in PATH to link build script binaries.
        """
        if shutil.which("cc"):
            return

        # Find or install clang, then create a cc symlink
        clang_path = self._find_clang()
        if not clang_path and shutil.which("brew"):
            self.output.info("Installing ohos-sdk + llvm-gcc-compat via harmonybrew...")
            self.run("brew install ohos-sdk")
            self.run("brew install llvm-gcc-compat")
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

    def _fix_libstdcxx(self):
        """Redirect -lstdc++ → -lc++_shared so Rust binaries link on OHOS.

        rustc adds `-lstdc++` to every linker invocation, but OHOS uses libc++
        (LLVM) instead of libstdc++ (GCC). This method:
        1. Creates libstdc++.so → INPUT(-lc++_shared) linker scripts in the
           rustc target lib directory (already in the linker's -L search path).
        2. Falls back to writing into a local dir and adding it to cargo's
           [target.<triple>.rustflags] via .cargo/config.toml.
        """
        # Step 1: try rustc sysroot (use self.run so conan's PATH is active)
        sysroot = None
        try:
            output = self.run("rustc --print sysroot", cwd=self.source_folder)
            sysroot = output.strip()
        except Exception:
            pass

        target = "aarch64-unknown-linux-ohos"
        if sysroot:
            lib_dir = os.path.join(sysroot, "lib", "rustlib", target, "lib")
            if os.path.isdir(lib_dir):
                self._write_libstdcxx_redirect(lib_dir)
                return

        # Step 2: fallback — write redirect into a local dir and inject via cargo config
        self.output.info("Falling back to cargo config for -lstdc++ redirect")
        redirect_dir = os.path.join(self.source_folder, "._libstdcxx")
        os.makedirs(redirect_dir, exist_ok=True)
        self._write_libstdcxx_redirect(redirect_dir)

        home = os.path.expanduser("~")
        cargo_config = os.path.join(home, ".cargo", "config.toml")
        cargo_config_dir = os.path.dirname(cargo_config)
        os.makedirs(cargo_config_dir, exist_ok=True)

        target_rustflags = (
            f'[target.{target}]\n'
            f'rustflags = ["-L", "{redirect_dir}"]\n'
        )
        # Append; if the section already exists, prepend a newline
        existing = ""
        if os.path.isfile(cargo_config):
            existing = Path(cargo_config).read_text(encoding="utf-8")
            if target not in existing:
                existing += "\n"
        with open(cargo_config, "w") as f:
            f.write(existing + target_rustflags)
        self.output.info(f"Added [target.{target}] rustflags to {cargo_config}")

    def _write_libstdcxx_redirect(self, lib_dir):
        """Write libstdc++.so/.a linker scripts pointing to libc++ into lib_dir."""
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

    def _find_clang(self):
        """Locate clang binary on the system. Returns path or None."""
        # 1. Check PATH
        clang = shutil.which("clang")
        if clang:
            return clang

        home = os.path.expanduser("~")
        # 2. OHOS SDK Cellar path
        import glob
        for cellar in glob.glob(os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk", "*", "native", "llvm")):
            candidate = os.path.join(cellar, "bin", "clang")
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        # 3. harmonybrew bin
        candidate = os.path.join(home, ".harmonybrew", "bin", "clang")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

        # 4. From rustc sysroot
        sdk_lib = self._find_ohos_lib_dir()
        if sdk_lib:
            llvm_bin = os.path.normpath(os.path.join(sdk_lib, "..", "..", "bin"))
            candidate = os.path.join(llvm_bin, "clang")
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        return None

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
