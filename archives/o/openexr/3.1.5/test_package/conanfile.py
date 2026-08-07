#!/usr/bin/env python3
"""Conan test_package for openexr -- verifies the library is usable.

This test exercises the OpenEXR API by:
1. Creating an Imf::Header object and verifying data window dimensions
2. Using Imf::Array2D template to verify array API availability
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class OpenexrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        # R34: test must actually depend on the package
        self.requires(self.tested_reference_str)
        # Also require Imath explicitly so its include dirs are available
        # (OpenEXR headers include <ImathVec.h> without Imath/ prefix)
        self.requires("imath/3.2.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: defer execution to a HarmonyOS PC device")
            return
        # R33: use env="conanrun" not shell env vars
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_openexr"),
            env="conanrun",
        )
