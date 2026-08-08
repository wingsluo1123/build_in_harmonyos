#!/usr/bin/env python3
"""Test package for postgresql-shared_ispell — loads .so via dlopen and checks symbols."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
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
        # Find the .so file in the package
        pkg_name = "postgresql-shared_ispell"
        dep = self.dependencies[pkg_name]
        pkg_folder = str(dep.package_folder) if dep.package_folder else ""

        so_path = None
        if pkg_folder and os.path.isdir(pkg_folder):
            for root, dirs, files in os.walk(pkg_folder):
                for f in files:
                    if f.startswith("shared_ispell") and f.endswith(".so"):
                        so_path = os.path.join(root, f)
                        break

        if not so_path:
            raise Exception("shared_ispell.so not found in package!")

        self.output.info(f"Testing with .so: {so_path}")

        # Run the test binary with the .so path
        # The binary is built by CMake in the build folder
        bin_path = os.path.join(self.build_folder, "test_package")
        self.run(f'"{bin_path}" "{so_path}"')
