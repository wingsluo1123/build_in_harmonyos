#!/usr/bin/env python3
"""Conan recipe for bandwhich 0.23.0 — a Rust/Cargo CLI tool for network bandwidth monitoring.

Build system: Cargo (Rust)
Product: Executable (bandwhich)
Dependencies: libpcap (system, for pnet crate)
"""
import os
import glob
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BandwhichConan(ConanFile):
    name = "bandwhich"
    version = "0.23.0"
    description = "Display current network utilization by process, connection and remote IP/hostname"
    license = "MIT"
    homepage = "https://github.com/imsnif/bandwhich"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libpcap is a system-level dependency, not a Conan package.
        # The pnet Rust crate links against it at build time.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_rust_toolchain(self):
        """Ensure Rust toolchain (cargo + rustc) is available."""
        try:
            subprocess.run(["cargo", "--version"], check=True,
                          capture_output=True, timeout=10)
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try installing via Homebrew (Harmonybrew)
        brew_paths = [
            "/storage/Users/currentUser/.harmonybrew/bin/brew",
            os.path.expanduser("~/.harmonybrew/bin/brew"),
        ]
        brew = None
        for path in brew_paths:
            if os.path.isfile(path):
                brew = path
                break

        if brew:
            self.run(f'{brew} install rust libpcap 2>&1 || true')
            brew_prefix = subprocess.run(
                [brew, "--prefix"], capture_output=True, text=True
            ).stdout.strip()
            os.environ["PATH"] = f"{brew_prefix}/bin:{os.environ.get('PATH', '')}"
        else:
            # Try installing Homebrew first
            self.run('zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)" 2>&1 || true')
            brew = "/storage/Users/currentUser/.harmonybrew/bin/brew"
            if os.path.isfile(brew):
                self.run(f'{brew} install rust libpcap 2>&1 || true')
                brew_prefix = subprocess.run(
                    [brew, "--prefix"], capture_output=True, text=True
                ).stdout.strip()
                os.environ["PATH"] = f"{brew_prefix}/bin:{os.environ.get('PATH', '')}"

    def _setup_libpcap_env(self):
        """Set up environment for cargo to find libpcap."""
        brew_paths = [
            "/storage/Users/currentUser/.harmonybrew/bin/brew",
            os.path.expanduser("~/.harmonybrew/bin/brew"),
        ]
        for brew in brew_paths:
            if not os.path.isfile(brew):
                continue
            try:
                prefix = subprocess.run(
                    [brew, "--prefix", "libpcap"],
                    capture_output=True, text=True, timeout=10
                ).stdout.strip()
                if prefix and os.path.isdir(prefix):
                    lib_dir = os.path.join(prefix, "lib")
                    pkgconfig_dir = os.path.join(lib_dir, "pkgconfig")
                    if os.path.isdir(pkgconfig_dir):
                        existing = os.environ.get("PKG_CONFIG_PATH", "")
                        os.environ["PKG_CONFIG_PATH"] = (
                            f"{pkgconfig_dir}:{existing}" if existing else pkgconfig_dir
                        )
                    if os.path.isdir(lib_dir):
                        existing = os.environ.get("LIBRARY_PATH", "")
                        os.environ["LIBRARY_PATH"] = (
                            f"{lib_dir}:{existing}" if existing else lib_dir
                        )
                    inc_dir = os.path.join(prefix, "include")
                    if os.path.isdir(inc_dir):
                        existing = os.environ.get("C_INCLUDE_PATH", "")
                        os.environ["C_INCLUDE_PATH"] = (
                            f"{inc_dir}:{existing}" if existing else inc_dir
                        )
                    break
            except Exception:
                pass

    def generate(self):
        # Set up environment for libpcap
        self._setup_libpcap_env()

    def build(self):
        apply_conandata_patches(self)
        # Ensure Rust toolchain is available
        self._ensure_rust_toolchain()
        # Set up libpcap environment
        self._setup_libpcap_env()
        # Create .cargo/config.toml for USTC mirror and clang linker
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        cargo_config = os.path.join(cargo_dir, "config.toml")
        with open(cargo_config, "w") as f:
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
                '[target.aarch64-unknown-linux-ohos]\n'
                'linker = "clang"\n'
                'ar = "llvm-ar"\n'
                'rustflags = [\n'
                '    "-C", "link-arg=-fuse-ld=lld",\n'
                '    \'--check-cfg=cfg(target_os, values("ohos"))\',\n'
                '    \'--check-cfg=cfg(target_env, values("ohos"))\',\n'
                ']\n'
            )
        # Build with cargo
        self.run("cargo build --release")

    def package(self):
        # The binary may be in source_folder/target/release or build_folder/target/release
        search_dirs = [
            os.path.join(self.source_folder, "target", "release"),
            os.path.join(self.build_folder, "target", "release"),
        ]
        found = False
        for search_dir in search_dirs:
            binary = os.path.join(search_dir, "bandwhich")
            if os.path.isfile(binary):
                copy(self, "bandwhich", src=search_dir, dst=os.path.join(self.package_folder, "bin"))
                found = True
                break
        if not found:
            pattern = os.path.join(self.source_folder, "**", "release", "bandwhich")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                src_dir = os.path.dirname(matches[0])
                copy(self, "bandwhich", src=src_dir, dst=os.path.join(self.package_folder, "bin"))
                found = True
        if not found:
            raise Exception("bandwhich binary not found after build")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
