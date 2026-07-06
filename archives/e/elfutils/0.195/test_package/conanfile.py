#!/usr/bin/env python3
"""Conan test_package — elfutils 0.195 (libraries + CLI tools).

L1 test: run readelf --version to verify the built binary works.
Also compile a small C program that uses libelf API.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ElfutilsTestConan(ConanFile):
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
        # Run readelf --version from the installed package
        dep = self.dependencies["elfutils"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        readelf = os.path.join(bin_dir, "eu-readelf")

        result = subprocess.run(
            [readelf, "--version"],
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        assert "0.195" in output, f"Expected '0.195' in readelf output, got: {output[:200]}"
        self.output.info("✅ readelf --version passed")

        # Also run the compiled libelf test
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_elfutils"), env="conanrun")
