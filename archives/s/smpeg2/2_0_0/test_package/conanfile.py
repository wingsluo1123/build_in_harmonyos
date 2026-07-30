#!/usr/bin/env python3
"""Conan test_package for smpeg2 2.0.0."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Smpeg2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_smpeg2" + suffix)
        if not os.path.isfile(bin_path):
            raise ConanInvalidConfiguration(f"Missing built test executable: {bin_path}")
        if can_run(self):
            self.run(bin_path, env="conanrun")
