#!/usr/bin/env python3
"""Conan CMake test package recipe for Paho MQTT C on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PahoMqttCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    options = {"with_ssl": [True, False]}
    default_options = {"with_ssl": False}

    def requirements(self):
        self.requires(
            self.tested_reference_str,
            options={"shared": False, "with_ssl": self.options.with_ssl},
        )
        if self.options.with_ssl:
            self.requires("openssl/3.5.8.1", options={"shared": False})

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["PAHO_TEST_WITH_SSL"] = self.options.with_ssl
        if self.options.with_ssl:
            tc.variables["PAHO_OPENSSL_INCLUDE_DIR"] = (
                self.dependencies["openssl"].package_folder.replace("\\", "/")
                + "/include"
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Skipping device integration execution because this host cannot run the HarmonyOS AArch64 binary"
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_paho_mqtt_c")
        self.run(executable, env="conanrun")
