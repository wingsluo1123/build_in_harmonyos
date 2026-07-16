#!/usr/bin/env python3
"""Conan recipe — chisel 2.0.1 (LLDB Python commands collection)."""

import os
from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ChiselConan(ConanFile):
    name = "chisel"
    version = "2.0.1"
    description = "Collection of LLDB commands to assist debugging iOS apps"
    license = "MIT"
    homepage = "https://github.com/facebook/chisel"
    url = ""

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
        # Chisel is a Python script collection — no compilation needed.
        # Verify Python syntax on all .py files.
        src = self.source_folder
        for root, _, files in os.walk(src):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    self.run(f"python3 -m py_compile {path}", cwd=src)

    def package(self):
        # Copy all .py files and supporting files to the package
        copy(self, "*.py", self.source_folder, os.path.join(self.package_folder, "libexec"))
        copy(self, "*.py", os.path.join(self.source_folder, "Chisel"),
             os.path.join(self.package_folder, "libexec", "Chisel"))
        copy(self, "*.py", os.path.join(self.source_folder, "commands"),
             os.path.join(self.package_folder, "libexec", "commands"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []