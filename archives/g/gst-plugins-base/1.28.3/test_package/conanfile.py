#!/usr/bin/env python3
"""Conan test_package — gst-plugins-base 1.28.3

Verifies that gst-plugins-base and its GStreamer dependency chain link
correctly. The test includes gst/gst.h (from gstreamer) and
gst/pbutils/pbutils.h (from gst-plugins-base), then calls gst_init()
and gst_pb_utils_init() to exercise APIs from both the tested package
and its dependency.
"""
from conan import ConanFile
from conan.tools.build import can_run, cross_building
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
        if cross_building(self) or not can_run(self):
            self.output.info(
                "cross-building / cannot run: only verify compile+link"
            )
            return
        cmake = CMake(self)
        cmake.test()
