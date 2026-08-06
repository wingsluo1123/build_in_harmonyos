#!/usr/bin/env python3
"""Conan recipe for extract-dtb — Python tool to extract DTB from kernel images.

This is a pure Python package built with setuptools (setup.py).
No C/C++ compilation is involved.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class ExtractDtbConan(ConanFile):
    name = "extract-dtb"
    version = "1.2"
    description = "Tool to split a kernel image with appended dtbs into separated kernel and dtb files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/PabloCastellano/extract-dtb"
    url = "https://github.com/PabloCastellano/extract-dtb"

    package_type = "application"

    # Python package — only need OS and arch for package ID
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Install Python package into a staging directory using pip
        # Use self.source_folder (not '.') since build_folder may differ
        install_dir = os.path.join(self.build_folder, "site-packages")
        self.run(
            f"pip install \"{self.source_folder}\" --target=\"{install_dir}\" --no-deps --no-build-isolation"
        )

    def package(self):
        install_dir = os.path.join(self.build_folder, "site-packages")
        # Copy installed Python packages and scripts
        copy(self, "*", src=install_dir, dst=os.path.join(self.package_folder, "site-packages"))
        # Copy bin/ scripts if they exist
        bin_dir = os.path.join(install_dir, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "*", src=bin_dir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # This is a Python application — expose bin/ and site-packages/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        # Set PYTHONPATH so the extract-dtb script can find its modules
        site_packages = os.path.join(self.package_folder, "site-packages")
        self.runenv_info.define_path("PYTHONPATH", site_packages)
