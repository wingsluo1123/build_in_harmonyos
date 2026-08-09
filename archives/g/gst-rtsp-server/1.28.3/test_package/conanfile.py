#!/usr/bin/env python3
"""Conan test_package for gst-rtsp-server 1.28.3.

Verifies that the gst-rtsp-server library can be linked and its
core API (gst_rtsp_server_new) is callable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstRtspServerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify library linkage and API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_gst_rtsp_server")
        self.run(test_bin, env="conanrun")
