#!/usr/bin/env python3
"""Conan recipe — hidapi 0.14.0 (CMake).

HIDAPI is a multi-platform library for communicating with USB and Bluetooth HID devices.
Uses hidraw backend only (libusb not available on HarmonyOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HidapiConan(ConanFile):
    name = "hidapi"
    version = "0.14.0"
    description = "Multi-platform library for communicating with USB and Bluetooth HID devices"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libusb/hidapi"
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
        tc.variables["HIDAPI_NO_ICONV"] = "ON"
        tc.variables["HIDAPI_WITH_LIBUSB"] = "OFF"
        tc.variables["HIDAPI_WITH_HIDRAW"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix src/CMakeLists.txt: HarmonyOS should use Linux path (hidraw, not libusb)
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        if os.path.isfile(src_cmake):
            # Add HarmonyOS to the Linux check so it uses hidraw backend
            replace_in_file(self, src_cmake,
                'if(CMAKE_SYSTEM_NAME MATCHES "Linux")',
                'if(CMAKE_SYSTEM_NAME MATCHES "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")')
            # Remove the else() block that forces HIDAPI_WITH_LIBUSB=ON for non-Linux
            replace_in_file(self, src_cmake,
                'set(HIDAPI_WITH_LIBUSB ON)',
                'set(HIDAPI_WITH_LIBUSB OFF)')

        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hidapi", "hidapi-hidraw"]
