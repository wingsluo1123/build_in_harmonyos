#!/usr/bin/env python3
"""Conan recipe for bruno-cli — npm CLI tool (Node.js).

Build system: npm (no C/C++ compilation)
Package type: executable/tool (JavaScript files)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrunocliConan(ConanFile):
    name = "bruno-cli"
    version = "3.4.2"
    description = "Bruno CLI — open-source API client for testing APIs"
    license = "MIT"
    homepage = "https://www.usebruno.com"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
