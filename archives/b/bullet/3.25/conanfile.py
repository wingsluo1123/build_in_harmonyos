#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Bullet, bullet, 3.25, bullet 3.25, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BulletConan(ConanFile):
    name = "bullet"
    version = "3.25"
    description = "bullet 3.25"
    license = "MIT"
    homepage = ""
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
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        tc.variables["CMAKE_INSTALL_PREFIX"] = "$DEFAULT_PREFIX"
        tc.variables["BUILD_CPU_DEMOS"] = "OFF"
        tc.variables["BUILD_OPENGL3_DEMOS"] = "OFF"
        tc.variables["BUILD_BULLET2_DEMOS"] = "OFF"
        tc.variables["BUILD_EXTRAS"] = "OFF"
        tc.variables["BUILD_UNIT_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["bullet"]
