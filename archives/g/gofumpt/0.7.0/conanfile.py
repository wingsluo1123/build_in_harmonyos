#!/usr/bin/env python3
"""Conan recipe for gofumpt — Go-based CLI formatter.

Build uses Go toolchain to compile gofumpt binary.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches
from conan.tools.layout import basic_layout


class GofumptConan(ConanFile):
    name = "gofumpt"
    version = "0.7.0"
    description = "gofumpt enforces a stricter format than gofmt"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mvdan/gofumpt"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self.run("go build -o gofumpt ./")

    def package(self):
        copy(self, "gofumpt", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # gofumpt is a CLI tool, not a library
        self.cpp_info.libs = []

    def package_id(self):
        self.info.clear()
