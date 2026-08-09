#!/usr/bin/env python3
"""Conan test_package for audiowaveform 1.10.3.

Since audiowaveform is a command-line application (not a library),
the test verifies that the audiowaveform binary is installed and runnable.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudiowaveformTestConan(ConanFile):
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
        # R34: Execute the audiowaveform binary to verify package usability
        self.run("audiowaveform --help", env="conanrun")
