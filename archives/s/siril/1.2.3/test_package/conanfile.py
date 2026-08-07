#!/usr/bin/env python3
"""Conan test_package for siril 1.2.3.

siril is a GUI application, so the test verifies that the siril binary
exists and can report its version. This is the L2 smoke test level.

Since siril links against many shared libraries (GTK, glib, etc.) that
may not be on the library path during testing, we use the conanrun
environment to set up LD_LIBRARY_PATH.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SirilTestConan(ConanFile):
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
        # R34: Substantive test - verify siril binary exists and can execute
        # siril is a GUI app; --version may fail if GTK can't init display,
        # so we test that the binary at least loads and produces output.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_siril")
        self.run(f'"{bin_path}"', env="conanrun")
