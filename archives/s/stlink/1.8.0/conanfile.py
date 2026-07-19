#!/usr/bin/env python3
"""Conan recipe for the stlink STM32 programmer toolkit (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class StlinkConan(ConanFile):
    name = "stlink"
    version = "1.8.0"
    description = "STM32 MCU programmer toolkit (st-flash, st-info, st-util)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stlink-org/stlink"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("libusb", "cmake_file_name", "LibUSB")
        deps.set_property("libusb", "cmake_target_name", "LibUSB::LibUSB")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["STLINK_BUILD_SHARED_LIBS"] = False
        tc.variables["STLINK_BUILD_TESTING"] = False
        tc.variables["STLINK_GUI"] = False
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
        self.cpp_info.libs = ["stlink"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.executables = ["st-flash", "st-util", "st-info"]
        self.cpp_info.set_property("cmake_file_name", "stlink")
        self.cpp_info.set_property("cmake_target_name", "stlink::stlink")
        self.cpp_info.requires = ["libusb::libusb"]
