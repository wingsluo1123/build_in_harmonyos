#!/usr/bin/env python3
"""Conan recipe for catch2 2.13.10-r0 (header-only CMake)."""

import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain


class Catch2Recipe(ConanFile):
    name = "catch2"
    version = "2.13.10-r0"
    package_type = "header-library"

    description = "A modern, C++-native, header-only, test framework for unit-tests"
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("testing", "unit-testing", "header-only")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_EXAMPLES"] = False
        tc.variables["CATCH_INSTALL_DOCS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []