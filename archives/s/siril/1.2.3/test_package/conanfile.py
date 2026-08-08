#!/usr/bin/env python3
"""Conan test_package for siril 1.2.3.

siril is a GUI application (package_type=application), not a library.
CMakeDeps does not populate siril_BINDIR for application packages (no libs
→ empty BIN_DIRS), so we pass the binary path directly as a CMake cache
variable derived from the siril package folder.
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
        # Pass the siril binary directory as a CMake cache variable.
        # For application packages, CMakeDeps does not expose siril_BINDIR,
        # so we derive it directly from the dependency package folder.
        siril_bindir = os.path.join(self.dependencies["siril"].package_folder, "bin")
        cmake.configure(cli_args=[f"-DSIRIL_BINDIR={siril_bindir}"])
        cmake.build()

    def test(self):
        # R34: Substantive test - verify siril binary exists and can execute
        # siril is a GUI app; --version may fail if GTK can't init display,
        # so we test that the binary at least loads and produces output.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_siril")
        self.run(f'"{bin_path}"', env="conanrun")
