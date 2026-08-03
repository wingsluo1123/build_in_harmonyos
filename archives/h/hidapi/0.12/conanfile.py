#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Hidapi, hidapi, 0.12, hidapi 0.12, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HidapiConan(ConanFile):
    name = "hidapi"
    version = "0.12"
    description = "hidapi 0.12"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        # CMAKE_POLICY_VERSION_MINIMUM must be a cache variable (-D) to
        # bypass cmake_minimum_required(VERSION 3.1.3) on CMake >= 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["HIDAPI_NO_ICONV"] = "ON"
        tc.variables["HIDAPI_WITH_LIBUSB"] = "OFF"
        tc.variables["HIDAPI_WITH_HIDRAW"] = "ON"
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
        # hidraw backend is the only one built (HIDAPI_WITH_LIBUSB=OFF),
        # so the installed library is libhidapi-hidraw.a
        self.cpp_info.libs = ["hidapi-hidraw"]
