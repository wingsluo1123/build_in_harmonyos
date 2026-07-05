#!/usr/bin/env python3
"""Conan recipe — bgrep 0.2 (simple Makefile binary tool)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BgrepConan(ConanFile):
    name = "bgrep"
    version = "0.2"
    description = "二进制 grep — 在文件中搜索二进制/十六进制字符串"
    license = "BSD"
    homepage = ""
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
        self.run("make CC=clang -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "bgrep", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
