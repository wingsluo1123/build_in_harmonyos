#!/usr/bin/env python3
"""POA CMake consumer and installed CLI/data regression tests."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
import os
import shlex
import sys


class PoaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
            package = self.dependencies["poa"].package_folder
            binary = os.path.join(package, "bin", "poa")
            data = os.path.join(package, "share", "poa")
            consumer = os.path.join(self.cpp.build.bindirs[0], "test_poa")
            self.run(f"{shlex.quote(consumer)} {shlex.quote(os.path.join(data, 'blosum80.mat'))}",
                     env="conanrun")
            args = [sys.executable, os.path.join(self.source_folder, "cli_regression.py"),
                    binary, data, os.path.join(self.source_folder, "data"),
                    os.path.join(self.build_folder, "packaged-cli-results")]
            self.run(" ".join(shlex.quote(arg) for arg in args), env="conanrun")
