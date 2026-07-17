#!/usr/bin/env python3
"""Conan recipe for libheif 1.22.2 — HEIF file format library.

All codecs disabled; provides HEIF container support only.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibheifConan(ConanFile):
    name = "libheif"
    version = "1.22.2"
    description = "HEIF file format library (codec-free build)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = ""

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["WITH_EXAMPLES"] = "OFF"
        tc.variables["WITH_GDK_PIXBUF"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["WITH_LIBDE265"] = "OFF"
        tc.variables["WITH_X265"] = "OFF"
        tc.variables["WITH_AOM_DECODER"] = "OFF"
        tc.variables["WITH_AOM_ENCODER"] = "OFF"
        tc.variables["WITH_X264"] = "OFF"
        tc.variables["WITH_DAV1D"] = "OFF"
        tc.variables["ENABLE_PLUGIN_LOADING"] = "OFF"
        tc.variables["WITH_LIBSHARPYUV"] = "OFF"
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
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
