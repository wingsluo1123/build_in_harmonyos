#!/usr/bin/env python3
"""Conan test_package for gst-plugins-bad 1.28.3.

Tests that the gst-plugins-bad codec parser library is usable.
Initializes GStreamer and exercises the H.264 NAL parser API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class GstPluginsBadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify the codec parser API works
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_bad")
        self.run(exe, env="conanrun")
