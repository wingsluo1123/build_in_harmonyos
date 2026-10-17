#!/usr/bin/env python3
"""Consumer of the experimental installed temperature implementation."""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class XmbmonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "measurement_consumer.c", "test_native.py", "test_fan_snapshot.py"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self, generator="Unix Makefiles").generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("Native execution is required for the thermal-service consumer")
        if can_run(self):
            command = [sys.executable, os.path.join(self.source_folder, "test_native.py"),
                       "--prefix", self.dependencies["xmbmon"].package_folder,
                       "--consumer", os.path.join(self.build_folder, "measurement_consumer"),
                       "--report", os.path.join(self.build_folder, "native-functional.json")]
            self.run(" ".join(shlex.quote(part) for part in command), env="conanrun")
            command = [sys.executable, os.path.join(self.source_folder, "test_fan_snapshot.py"),
                       "--prefix", self.dependencies["xmbmon"].package_folder,
                       "--report", os.path.join(self.build_folder, "fan-snapshot-contract.json")]
            self.run(" ".join(shlex.quote(part) for part in command), env="conanrun")
