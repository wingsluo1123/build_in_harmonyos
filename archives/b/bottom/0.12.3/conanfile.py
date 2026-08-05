#!/usr/bin/env python3
"""Conan 2.x recipe — bottom 0.12.3 (Rust system monitor)

bottom is a cross-platform graphical process/system monitor for the terminal,
written in Rust. It builds a single binary `btm` via cargo.

Build system: cargo (Rust)
Product: executable (btm)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BottomConan(ConanFile):
    name = "bottom"
    version = "0.12.3"
    description = "A customizable cross-platform graphical process/system monitor for the terminal"
    license = "MIT"
    homepage = "https://github.com/ClementTsang/bottom"
    url = "https://github.com/ClementTsang/bottom"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Rust projects use cargo as build system.
        # cargo uses `cc` as default linker; ensure clang is used.
        self.run("cargo build --release --bin btm",
                  env=["CC=clang", "CXX=clang++"])

    def package(self):
        # cargo creates target/release/ relative to Cargo.toml directory.
        # With basic_layout, this may be in source_folder or build_folder.
        for folder in [self.source_folder, self.build_folder]:
            release_dir = os.path.join(folder, "target", "release")
            if os.path.isdir(release_dir):
                copy(self, "btm", release_dir, os.path.join(self.package_folder, "bin"))
                break

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
