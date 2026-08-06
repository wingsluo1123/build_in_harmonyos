#!/usr/bin/env python3
"""Test package for gst-libav 1.28.3 — verifies plugin loads and has GStreamer symbols.

R34: Test actually depends on the tested package by loading the
plugin .so via dlopen and checking for GStreamer plugin descriptor symbols.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstLibavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Set the plugin path environment variable for the test
        plugin_path = os.path.join(self.dependencies["gst-libav"].package_folder, "lib", "gstreamer-1.0")
        self.run(f"GST_LIBAV_PLUGIN_PATH={plugin_path} {os.path.join(self.cpp.build.bindirs[0], 'test_gst_libav')}", env="conanrun")
