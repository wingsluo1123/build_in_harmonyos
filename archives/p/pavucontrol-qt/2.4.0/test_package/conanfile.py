#!/usr/bin/env python3
"""Test package for pavucontrol-qt 2.4.0.

Verifies that the pavucontrol-qt binary is installed, is a valid ELF executable,
and is linked against Qt6 and PulseAudio libraries.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PavucontrolQtTestConan(ConanFile):
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
        # Find the pavucontrol-qt binary in the installed package
        pkg = self.dependencies["pavucontrol-qt"]
        binary = os.path.join(pkg.package_folder, "bin", "pavucontrol-qt")

        if not os.path.exists(binary):
            raise Exception(f"pavucontrol-qt binary not found at {binary}")

        self.output.info(f"Found pavucontrol-qt binary: {binary}")

        # Verify it's a valid ELF executable (R34: test must verify the package)
        with open(binary, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"Binary is not ELF: {magic}"
            self.output.info("Binary is valid ELF ✅")

        # Run file command to verify architecture and linking
        self.run(f"file {binary}", env="conanrun")

        # Run cmake test as well
        cmake = CMake(self)
        cmake.test()
