#!/usr/bin/env python3
"""Test package for gst-plugins-base 1.28.3 — verifies gst_app API."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class GstPluginsBaseTestConan(ConanFile):
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
        plugin_path = os.path.join(self.dependencies["gst-plugins-base"].package_folder, "lib", "gstreamer-1.0")
        self.run(f"GST_PLUGIN_PATH={plugin_path} {os.path.join(self.cpp.build.bindirs[0], 'test_gst_plugins_base')}", env="conanrun")
