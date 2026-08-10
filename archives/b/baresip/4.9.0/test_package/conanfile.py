#!/usr/bin/env python3
"""Conan test_package for baresip 4.9.0 — Conan L1 official test.

Verifies that baresip can be linked and its basic API works:
  - baresip_version() returns correct version string
  - conf_configure_buf() initializes config
  - baresip_init() + baresip_network() + baresip_close() works
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BaresipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Also require re directly so CMakeDeps generates its config
        # and its include dirs are available in the test build
        self.requires("re/4.9.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_baresip", env="conanrun")
