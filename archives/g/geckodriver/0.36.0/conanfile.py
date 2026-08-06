#!/usr/bin/env python3
"""Conan 2.x recipe — geckodriver 0.36.0 (Mozilla WebDriver for Firefox)

geckodriver is a Rust binary that implements the WebDriver protocol
to control Gecko-based browsers (Firefox). It is built with Cargo.

Build: cargo build --release
Output: target/release/geckodriver (ELF binary)
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GeckodriverConan(ConanFile):
    name = "geckodriver"
    version = "0.36.0"
    description = "Mozilla WebDriver proxy for Gecko-based browsers (Firefox)"
    license = "MPL-2.0"
    homepage = "https://github.com/mozilla/geckodriver"
    url = "https://cnb.cool/OpenHarmonyPCDeveloper/build_in_harmonyos/-/tree/main/archives/g/geckodriver"

    package_type = "application"  # CLI tool, not a library

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

    def build(self):
        apply_conandata_patches(self)
        # Cargo manages its own dependencies and toolchain.
        # The binary is a standalone ELF executable (no shared lib deps).
        self.run("cargo build --release")

    def package(self):
        # Cargo creates target/release/ relative to the build directory.
        # With basic_layout(), conan may create a build-type subdirectory,
        # so we search for the binary in the build folder and its parent.
        search_dirs = [
            os.path.join(self.build_folder, "target", "release"),
            os.path.join(os.path.dirname(self.build_folder), "target", "release"),
        ]
        for target_dir in search_dirs:
            if os.path.isfile(os.path.join(target_dir, "geckodriver")):
                copy(self, "geckodriver", target_dir, os.path.join(self.package_folder, "bin"))
                return
        # Fallback: recursive glob search
        pattern = os.path.join(os.path.dirname(self.build_folder), "**", "target", "release", "geckodriver")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            copy(self, "geckodriver", os.path.dirname(matches[0]), os.path.join(self.package_folder, "bin"))
        else:
            raise ConanException("geckodriver binary not found — cargo build may have failed or output path mismatch")

    def package_info(self):
        # CLI tool: expose bin directory, not libs
        self.cpp_info.bindirs = ["bin"]
