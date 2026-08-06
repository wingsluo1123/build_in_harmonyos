#!/usr/bin/env python3
"""Test package for imagemagick-full 7.1.2-23.

Verifies that the ImageMagick binary and libraries work correctly.
Runs `magick --version` to check delegates and version.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ImagemagickFullTestConan(ConanFile):
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
        # Run the compiled test binary that uses MagickWand API
        cmake = CMake(self)
        cmake.test()
        # Also verify the magick binary works
        self.run("magick --version", env="conanrun")
