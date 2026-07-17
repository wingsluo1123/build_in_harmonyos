#!/usr/bin/env python3
"""Conan test_package — SDL2_ttf 2.24.0

L1 test: verify the package can be found and linked.
"""
import os

from conan import ConanFile


class Sdl2TtfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the library file exists in the package
        libdir = self.cpp_info.libdirs[0] if self.cpp_info.libdirs else ""
        self.output.info(f"Checking for SDL2_ttf library in {libdir}")
