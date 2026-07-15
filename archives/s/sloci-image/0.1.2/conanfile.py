#!/usr/bin/env python3
"""Conan recipe for sloci-image — a POSIX shell script tool
for creating single-layer OCI images.

Since sloci-image is a pure shell script, this recipe installs it by
copying the script to the bin directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, copy
from conan.tools.layout import basic_layout


class SlociImageConan(ConanFile):
    name = "sloci-image"
    version = "0.1.2"
    description = "Simple script for creating single-layer OCI images"
    license = "MIT"
    homepage = "https://github.com/jirutka/sloci-image"
    url = "https://github.com/jirutka/sloci-image"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Copy the shell script to the bin directory
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "sloci-image", src=self.source_folder, dst=bin_dir)
        script_path = os.path.join(bin_dir, "sloci-image")
        os.chmod(script_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
