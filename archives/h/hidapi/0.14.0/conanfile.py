#!/usr/bin/env python3
"""Conan recipe — hidapi 0.14.0 (CMake).

HIDAPI is a multi-platform library for communicating with USB and Bluetooth HID devices.
Uses hidraw backend only (libusb not available on HarmonyOS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
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
        self.cpp_info.libs = ["hidapi", "hidapi-hidraw"]
