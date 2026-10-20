#!/usr/bin/env python3
"""Conan consumer tests for glib2 2.80.0."""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Glib2TestConan(ConanFile):
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
        if str(self.settings.os) == "OHOS":
            # HarmonyOS /system/bin/sh (mksh) cannot launch ELF test binaries.
            # Run both consumer programs through the same Bash wrapper used by
            # the existing GLib HarmonyOS package.
            bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                    or "/data/service/hnp/bin/bash")
            self.run(f"{bash} -c './test_glib2 && ./test_glib_harmonyos'", env="conanrun")
        else:
            self.run("./test_glib2", env="conanrun")
