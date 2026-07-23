#!/usr/bin/env python3
"""Conan test_package for ElaWidgetTools 2.0.0.

Tests that the ElaWidgetTools library can be linked and its API called.
Qt5 is a system-installed dependency (not available as Conan package).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ElaWidgetToolsTestConan(ConanFile):
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
        # Qt5 runtime: set library path and plugin path
        qt5_home = os.path.expanduser("~/usr/local/Qt5")
        qt5_lib = os.path.join(qt5_home, "lib")

        # Build a shell command that sets env vars then runs the test
        test_bin = os.path.join(self.build_folder, "test_ElaWidgetTools")
        cmd = (
            f"export LD_LIBRARY_PATH={shlex.quote(qt5_lib)}:$LD_LIBRARY_PATH && "
            f"export QT_PLUGIN_PATH={shlex.quote(os.path.join(qt5_home, 'plugins'))} && "
            f"export QT_QPA_PLATFORM=offscreen && "
            f"{shlex.quote(test_bin)}"
        )
        self.run(cmd)
