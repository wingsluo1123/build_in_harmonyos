#!/usr/bin/env python3
"""Conan recipe — git-cliff 2.10.1

A highly customizable changelog generator for Rust projects.
Cargo/Rust workspace project. Builds a single binary: git-cliff.
License: MIT OR Apache-2.0
Homepage: https://github.com/orhun/git-cliff
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


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

    def generate(self):
        # Ensure Rust toolchain is discoverable.
        # On OHOS, cargo/rustc may be installed via Harmonybrew or as system symlinks.
        env = Environment()
        for candidate in [
            os.path.expanduser("~/.harmonybrew/bin"),
            "/storage/Users/currentUser/.harmonybrew/bin",
            "/storage/Users/currentUser/usr/local/bin",
        ]:
            if os.path.isdir(candidate):
                env.append_path("PATH", candidate)
        env.vars(self).save_script("cargo_env")

    def build(self):
        apply_conandata_patches(self)
        # Cargo manages its own toolchain, flags, and dependency resolution.
        # env="conanbuild" activates the PATH from generate() so cargo is found.
        self.run("cargo build --release", env="conanbuild")

    def package(self):
        # Copy the release binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "git-cliff", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
