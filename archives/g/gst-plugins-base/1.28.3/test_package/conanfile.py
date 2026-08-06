#!/usr/bin/env python3
"""Conan test_package — gst-plugins-base 1.28.3

Tests that gst-plugins-base support libraries can be linked and their APIs
called. Specifically calls gst_audio_format_to_string() and
gst_audio_format_get_info() from the gstaudio-1.0 library.

Note: gstreamer is explicitly required because gst-plugins-base headers
transitively include gst/gst.h from the gstreamer package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstPluginsBaseTestConan(ConanFile):
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
        # Run the test binary directly to verify the library API works
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_base"), env="conanrun")
