#!/usr/bin/env python3
"""CMake consumer test for Qt MQTT 6.11.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtMqttTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qt6mqtt = self.dependencies["qt6-mqtt"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6Mqtt_DIR"] = os.path.join(
            qt6mqtt, "lib", "cmake", "Qt6Mqtt"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qt6-mqtt test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_package")
            self.run(executable, env="conanrun", ignore_errors=False)
