"""Conan runtime test for teensy_loader_cli.

L1 smoke test: builds the C test (test_package.c) which verifies the packaged
`teensy_loader_cli --list-mcus` output (Supported MCUs / atmega32u4 /
at90usb1286), then runs test.sh for additional CLI assertions.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TeensyLoaderCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
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
            executable = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(executable, env="conanrun")
            self.run("sh test.sh", env="conanrun")
