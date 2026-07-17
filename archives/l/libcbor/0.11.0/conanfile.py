#!/usr/bin/env python3
"""Conan recipe — libcbor 0.11.0 (CMake, static library).

libcbor is a C library for parsing and generating CBOR.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcborConan(ConanFile):
    name = "libcbor"
    version = "0.11.0"
    description = "C library for parsing and generating CBOR (RFC 7049)"
    license = "MIT"
    homepage = "https://github.com/PJK/libcbor"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["WITH_TESTS"] = "OFF"
        tc.variables["WITH_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cbor"]
        self.cpp_info.set_property("pkg_config_name", "libcbor")
        self.cpp_info.set_property("cmake_target_name", "libcbor::libcbor")
