#!/usr/bin/env python3
"""Conan recipe for cxxopts 3.2.1 — Lightweight C++ command-line option parser.

cxxopts is a header-only C++ library for parsing command-line options.
It provides a single header file (cxxopts.hpp) that can be included directly.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CxxoptsConan(ConanFile):
    name = "cxxopts"
    version = "3.2.1"
    description = "Lightweight C++ command-line option parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/jarro2783/cxxopts"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass  # Header-only library, no build step

    def package(self):
        copy(self, "cxxopts.hpp", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cxxopts")
        self.cpp_info.set_property("cmake_target_name", "cxxopts::cxxopts")
