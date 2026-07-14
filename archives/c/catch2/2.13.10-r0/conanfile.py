#!/usr/bin/env python3
"""Conan recipe — catch2 2.13.10-r0 (CMake)"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get


class Catch2Recipe(ConanFile):
    name = "catch2"
    version = "2.13.10-r0"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = ()
    generators = ()
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "BSL-1.0"
    description = "A modern, C++-native, header-only, test framework for unit-tests"
    topics = ("testing", "unit-testing", "header-only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_EXAMPLES"] = False
        tc.variables["CATCH_INSTALL_DOCS"] = False
        tc.generate()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
