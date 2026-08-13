#!/usr/bin/env python3
"""Conan test_package for ffms2 5.0 — L1 official test.

Verifies that the ffms2 library is correctly packaged and its API
(FFMS_Init, FFMS_GetVersion, FFMS_GetLogLevel, FFMS_SetLogLevel,
FFMS_CreateIndexer) can be called from a consumer program.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


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
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # Run the test executable directly via self.run() so the L0d gate
        # detects an actual test invocation (cmake.test() is not recognized).
        # env="conanrun" loads conanrunenv script which sets LD_LIBRARY_PATH
        # to include the ffms2 and all transitive dependency lib dirs.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_ffms2")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c '{exe}'", env="conanrun")
