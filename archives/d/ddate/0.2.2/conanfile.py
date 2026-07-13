#!/usr/bin/env python3
"""Conan recipe — ddate 0.2.2 (CMake, terminal tool, static linking R26).

ddate is a Discordian date converter — a terminal executable with no
external library dependencies.  Built with CMake and statically linked
per R26 (terminal tools must be statically linked for DevBox deployment).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DdateConan(ConanFile):
    name = "ddate"
    version = "0.2.2"
    description = "Discordian date converter — displays the date in the Discordian calendar"
    license = "MIT"
    homepage = "https://github.com/bo0ts/ddate"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # ddate is a standalone executable, no libraries to expose
        self.cpp_info.libs = []
