#!/usr/bin/env python3
"""Conan test_package — gst-plugins-ugly 1.28.3.

L1 test: verifies that gst-plugins-ugly builds and the ASF plugin
can be statically registered with GStreamer.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstPluginsUglyTestConan(ConanFile):
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
        # Run the test binary directly (R34: real API test)
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_ugly"),
            env="conanrun",
        )
