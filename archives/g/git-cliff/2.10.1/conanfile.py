#!/usr/bin/env python3
"""Conan recipe — git-cliff 2.10.1

A highly customizable changelog generator for Rust projects.
Cargo/Rust workspace project. Builds a single binary: git-cliff.
License: MIT OR Apache-2.0
Homepage: https://github.com/orhun/git-cliff
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException


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
        # Rust crate dependencies are managed by Cargo via Cargo.lock, not Conan.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_cargo(self):
        """Find the cargo binary, checking PATH and common installation locations."""
        cargo = shutil.which("cargo")
        if cargo:
            return cargo
        for candidate in [
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
        ]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException(
            "cargo not found. Install Rust toolchain: "
            "zsh -c \"$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)\" && "
            "eval \"$(/storage/Users/currentUser/.harmonybrew/bin/brew shellenv)\" && "
            "brew install rust"
        )

    def build(self):
        apply_conandata_patches(self)
        cargo = self._find_cargo()
        # Use full path to cargo to avoid PATH issues in CI environments.
        # R33: No reliance on shell env vars for compiler flags.
        self.run(f'"{cargo}" build --release')

    def package(self):
        # Copy the release binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "git-cliff", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
