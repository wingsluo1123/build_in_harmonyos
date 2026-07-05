#!/usr/bin/env python3
"""Conan recipe — borgbackup 1.4.4 (Python package).
Note: Requires Python dev headers and Cython which are not available on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BorgbackupConan(ConanFile):
    name = "borgbackup"
    version = "1.4.4"
    description = "Deduplicating backup program with compression and authenticated encryption"
    license = "MIT"
    homepage = "https://www.borgbackup.org/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # borgbackup is a Python package with C extensions (Cython)
        # Build using pip install with proper error handling
        self.run("pip3 install . --no-build-isolation", cwd=self.source_folder)

    def package(self):
        # Copy Python package files
        copy(self, "*.py", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.so", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = []
