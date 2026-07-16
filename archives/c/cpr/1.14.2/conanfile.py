#!/usr/bin/env python3
"""Conan recipe for cpr 1.14.2 — C++ Requests: Curl for People.

Build system: CMake, C++17.
Dependencies: curl/8.13.0 (system curl, not the built-in FetchContent one).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CprConan(ConanFile):
    name = "cpr"
    version = "1.14.2"
    description = "C++ Requests: Curl for People, a spiritual port of Python Requests"
    license = "MIT"
    homepage = "https://github.com/libcpr/cpr"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.13.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.get_safe("shared") else "OFF"
        tc.variables["CPR_USE_SYSTEM_CURL"] = "ON"
        tc.variables["CPR_ENABLE_SSL"] = "OFF"
        tc.variables["CPR_CURL_USE_LIBPSL"] = "OFF"
        tc.variables["CPR_BUILD_TESTS"] = "OFF"
        tc.variables["CPR_BUILD_MONGOOSE"] = "OFF"
        tc.variables["CPR_SKIP_CA_BUNDLE_SEARCH"] = "ON"
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
        self.cpp_info.libs = ["cpr"]