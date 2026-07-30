#!/usr/bin/env python3
"""Conan test package for log4cpp."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Log4cppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_log4cpp", env="conanrun")
