#!/usr/bin/env python3
"""Conan test_package — libdisplay-info 0.4.0.

L1 consumer test. It links the installed library, parses a real 256-byte
EDID (upstream's acer-p1276 fixture) and checks the values that the library
derives from it: the vendor table lookup (`Acer Technologies` comes from
hwdata's pnp.ids, i.e. the packaged build-time data dependency), the
product/serial strings (which upstream builds through its memory-stream
helper) and the rejection of malformed input.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdisplayInfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the consumer binary: it exercises di_info_parse_edid(),
        # di_info_get_make/model/serial(), di_edid_get_vendor_product() and
        # di_info_destroy() and returns non-zero if any value is wrong.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdisplay_info")
        self.run(test_bin, env="conanrun")
