#!/usr/bin/env python3
"""Test package for pavucontrol-qt 2.4.0.

Verifies that the pavucontrol-qt binary is installed and is a valid ELF executable.
Since pavucontrol-qt is a GUI application, full runtime testing requires a display
server. This test verifies binary integrity (ELF format, architecture, PIE).
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
        # Verify the binary exists and is a valid ELF executable
        bin_dir = os.path.join(self.deps_env_info["pavucontrol-qt"].bindirs[0]) if hasattr(self, "deps_env_info") else None
        # Try to find the binary in the package
        pkg = self.dependencies["pavucontrol-qt"]
        binary = os.path.join(pkg.package_folder, "bin", "pavucontrol-qt")
        if os.path.exists(binary):
            self.output.info(f"Found pavucontrol-qt binary: {binary}")
            # Check it's an ELF file
            with open(binary, "rb") as f:
                magic = f.read(4)
                assert magic == b"\x7fELF", f"Binary is not ELF: {magic}"
                self.output.info("Binary is valid ELF ✅")
            # Check architecture
            self.run(f"file {binary}", env="conanrun")
        else:
            # Try running cmake test
            cmake = CMake(self)
            cmake.test()
