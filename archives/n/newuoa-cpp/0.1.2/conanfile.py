#!/usr/bin/env python3
"""Conan recipe for newuoa-cpp 0.1.2 (C++ implementation of NEWUOA).

Upstream: https://github.com/elsid/newuoa-cpp
NEWUOA is a derivative-free trust-region optimizer (Powell's algorithm)
with both a plain C function interface and C++ closure interfaces.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NewuoacppConan(ConanFile):
    name = "newuoa-cpp"
    version = "0.1.2"
    description = "C++ implementation of NEWUOA derivative-free optimizer with C interface"
    license = "MIT"
    homepage = "https://github.com/elsid/newuoa-cpp"
    url = "https://github.com/elsid/newuoa-cpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["newuoa"]
        self.cpp_info.set_property("cmake_file_name", "newuoa-cpp")
        self.cpp_info.set_property("cmake_target_name", "newuoa::newuoa")
        self.cpp_info.set_property("pkg_config_name", "newuoa")