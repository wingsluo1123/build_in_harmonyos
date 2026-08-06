#!/usr/bin/env python3
"""Conan recipe — git-cliff 2.10.1

A highly customizable changelog generator for Rust projects.
Cargo/Rust workspace project. Builds a single binary: git-cliff.
License: MIT OR Apache-2.0
Homepage: https://github.com/orhun/git-cliff
"""
import os
import shutil
import subprocess
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException

# Harmonybrew install script
HOMEBREW_INSTALL = "https://harmonybrew.atomgit.com/install.sh"

# Cargo mirror config (crates.io is unreachable on OHOS network)
CARGO_CONFIG = """[source.crates-io]
replace-with = 'rsproxy-sparse'

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[net]
git-fetch-with-cli = true
"""


class GitCliffConan(ConanFile):
    name = "git-cliff"
    version = "2.10.1"
    description = "A highly customizable changelog generator — see your git history in style"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/orhun/git-cliff"
    url = "https://github.com/orhun/git-cliff"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_rust(self):
        """Find or install Rust toolchain. Returns cargo binary path."""
        # 1. Try existing cargo in PATH
        cargo = shutil.which("cargo")
        if cargo:
            return cargo

        # 2. Check Harmonybrew installation
        brew_cargo = "/storage/Users/currentUser/.harmonybrew/bin/cargo"
        if os.path.isfile(brew_cargo) and os.access(brew_cargo, os.X_OK):
            return brew_cargo

        # 3. Install Harmonybrew + Rust
        self.output.info("Rust toolchain not found, installing via Harmonybrew...")
        brew_bin = "/storage/Users/currentUser/.harmonybrew/bin"
        brew = os.path.join(brew_bin, "brew")

        if not os.path.isfile(brew):
            # Install Harmonybrew
            self.run(f'zsh -c "$(curl -fsSL {HOMEBREW_INSTALL})"')

        # Install Rust via brew
        self.run(f'eval "$({brew} shellenv)" && brew install rust 2>&1')

        if os.path.isfile(brew_cargo):
            return brew_cargo

        raise ConanException(
            "Failed to install Rust toolchain. "
            "Manual install: zsh -c \"$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)\" && "
            "brew install rust"
        )

    def _ensure_cc(self):
        """Ensure cc/c++ symlinks exist (cargo uses 'cc' as default linker)."""
        if shutil.which("cc"):
            return None

        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangpp = shutil.which("clang++") or "/data/service/hnp/bin/clang++"

        local_bin = os.path.join(self.build_folder, ".local-bin")
        os.makedirs(local_bin, exist_ok=True)

        cc_link = os.path.join(local_bin, "cc")
        cxx_link = os.path.join(local_bin, "c++")
        if not os.path.exists(cc_link) and os.path.isfile(clang):
            os.symlink(clang, cc_link)
        if not os.path.exists(cxx_link) and os.path.isfile(clangpp):
            os.symlink(clangpp, cxx_link)

        return local_bin

    def _setup_cargo_mirror(self):
        """Set up CARGO_HOME with rsproxy mirror config."""
        cargo_home = os.path.join(self.build_folder, ".cargo-home")
        config_path = os.path.join(cargo_home, "config.toml")

        if not os.path.isfile(config_path):
            os.makedirs(cargo_home, exist_ok=True)
            with open(config_path, "w") as f:
                f.write(CARGO_CONFIG)

        return cargo_home

    def build(self):
        apply_conandata_patches(self)

        cargo = self._ensure_rust()
        local_bin = self._ensure_cc()
        cargo_home = self._setup_cargo_mirror()

        # Build environment
        env = dict(os.environ)
        env["CARGO_HOME"] = cargo_home

        # Set up PATH
        paths = [os.path.dirname(cargo)]
        if local_bin:
            paths.append(local_bin)
        paths.append(env.get("PATH", ""))
        env["PATH"] = ":".join(paths)

        # Set RUSTC if we can find it
        rustc = shutil.which("rustc") or os.path.join(os.path.dirname(cargo), "rustc")
        if os.path.isfile(rustc):
            env["RUSTC"] = rustc

        # Run cargo build using subprocess for full environment control
        self.output.info(f"Running: {cargo} build --release")
        result = subprocess.run(
            [cargo, "build", "--release"],
            env=env,
            cwd=self.build_folder,
            capture_output=False,
        )
        if result.returncode != 0:
            raise ConanException(
                f"cargo build failed with exit code {result.returncode}"
            )

    def package(self):
        # Copy the release binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "git-cliff", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
