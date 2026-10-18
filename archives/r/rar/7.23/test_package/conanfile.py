#!/usr/bin/env python3
"""Conan test_package for rar 7.23 (RARLAB UnRAR CLI + libunrar).

Two layers:
  1. package integrity — bin/unrar, lib/libunrar.*, include/dll.hpp exist;
  2. on a machine that can run the target (can_run): test_rar.py drives the
     CMake-built libunrar consumer (test.cpp) and the packaged unrar CLI.
     See test_rar.py for the assertion inventory (11 checks, 4 of them
     HarmonyOS-specific).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class RarTestConan(ConanFile):
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
        package_folder = self.dependencies["rar"].package_folder
        exe = os.path.join(package_folder, "bin", "unrar")
        lib_dir = os.path.join(package_folder, "lib")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing unrar executable: {exe}")
        if not os.path.isfile(os.path.join(package_folder, "include", "dll.hpp")):
            raise AssertionError("Missing include/dll.hpp")
        if not (os.path.isfile(os.path.join(lib_dir, "libunrar.a"))
                or os.path.isfile(os.path.join(lib_dir, "libunrar.so"))):
            raise AssertionError("Missing libunrar library")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_rar")
        script = os.path.join(self.source_folder, "test_rar.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" TEST_BIN="{test_bin}" '
            f'"{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(f"rar test_package failed with exit code {result}")
