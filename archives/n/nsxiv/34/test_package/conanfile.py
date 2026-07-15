#!/usr/bin/env python3
"""Conan test_package — nsxiv 34

Compiles a test program that verifies the nsxiv binary exists and is a
valid ELF executable. Also attempts to run nsxiv -v for runtime check.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NsxivTestConan(ConanFile):
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
        # Get the nsxiv binary path from the dependency
        bin_dir = self.dependencies["nsxiv"].cpp_info.bindirs[0]
        nsxiv_bin = os.path.join(bin_dir, "nsxiv")

        # Run the compiled test binary with nsxiv path as argument
        test_bin = os.path.join(self.build_folder, "test_nsxiv")
        self.run(f'"{test_bin}" "{nsxiv_bin}"', env="conanrun")

        # Also try running nsxiv -v directly
        try:
            self.run(f'"{nsxiv_bin}" -v', env="conanrun")
        except Exception as e:
            self.output.info(f"nsxiv -v failed (may need X11 runtime libs): {e}")
