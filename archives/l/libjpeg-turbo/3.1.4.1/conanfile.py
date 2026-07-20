#!/usr/bin/env python3
"""Conan recipe for libjpeg-turbo 3.1.4.1 (CMake build system)."""
import os

from conan import ConanFile
from conan.tools.files import get, collect_libs
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibjpegturboConan(ConanFile):
    name = "libjpeg-turbo"
    version = "3.1.4.1"
    description = "JPEG image codec with SIMD acceleration"
    license = "BSD-3-Clause"
    homepage = "https://libjpeg-turbo.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_SIMD"] = False
        tc.variables["WITH_TESTS"] = False
        tc.variables["ENABLE_SHARED"] = self.options.shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libjpeg-turbo")
        self.cpp_info.set_property("pkg_config_name", "libjpeg")
