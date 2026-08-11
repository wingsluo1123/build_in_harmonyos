#!/usr/bin/env python3
"""Conan test_package for ffms2 5.0 — L1 official test.

Verifies that the ffms2 library is correctly packaged and its API
(FFMS_Init, FFMS_GetVersion, FFMS_GetLogLevel, FFMS_SetLogLevel,
FFMS_CreateIndexer) can be called from a consumer program.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Ffms2TestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
