#!/usr/bin/env python3
"""Conan test_package for audacious-plugins 4.5.1.

Verifies that the package contains valid .so plugin files (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudaciousPluginsTestConan(ConanFile):
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
        # Set plugin directory for the test binary
        plugin_dir = os.path.join(self.dependencies["audacious-plugins"].package_folder, "lib", "audacious")
        self.run(f"env AUDACIOUS_PLUGIN_DIR={plugin_dir} {os.path.join(self.cpp.build.bindirs[0], 'test_audacious-plugins')}", env="conanrun")
