#!/usr/bin/env python3
"""Conan test_package for SDL2_ttf 2.24.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Sdl2TtfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindirs[0], "test_sdl2_ttf")
            self.run(binary, env="conanrun", cwd=self.build_folder)
