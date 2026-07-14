#!/usr/bin/env python3
"""Conan test_package — sound-touch 2.4.0

L1 test: verify the packaged library can be found, linked, and the API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SoundTouchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_sound_touch")
        self.run(f'export LD_LIBRARY_PATH="{os.path.join(self.dependencies["sound-touch"].package_folder, "lib")}:$LD_LIBRARY_PATH"; {bin_path}', env="conanrun")
