#!/usr/bin/env python3
"""Conan recipe — bamtools 2.5.3 (CMake project).

bamtools is a CMake-based BAM file processing library and CLI tool.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class BamtoolsConan(ConanFile):
    name = "bamtools"
    version = "2.5.3"
    description = "BAM 文件处理工具库和命令行工具集"
    license = "MIT"
    homepage = "https://github.com/pezmaster31/bamtools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # bamtools CMake find_package(ZLIB) requires zlib
    requires = "zlib/1.3.1@ohpcd/stable"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # bamtools builds a static library by default
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()
        # Generate CMake dep files for zlib (find_package(ZLIB))
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["bamtools"]
