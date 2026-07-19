#!/usr/bin/env python3
"""Conan recipe for HackRF host tools and libhackrf (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class HackrfConan(ConanFile):
    name = "hackrf"
    version = "2024.02.1"
    description = "HackRF Software Defined Radio tools (hackrf_info, hackrf_transfer)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/greatscottgadgets/hackrf"
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
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "host"))
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hackrf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "hackrf")
        self.cpp_info.set_property("cmake_target_name", "hackrf::hackrf")
