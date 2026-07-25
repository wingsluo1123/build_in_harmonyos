#!/usr/bin/env python3
"""Conan test_package for rpm - verifies the rpm library links correctly."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RpmTestConan(ConanFile):
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
        # System packages are installed via cmd-pkgs, ensure their lib path is on LD_LIBRARY_PATH
        sys_prefix = os.environ.get("HNP_PREFIX")
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if sys_prefix:
            os.environ["LD_LIBRARY_PATH"] = sys_prefix + "/lib" + (":" + old_ld if old_ld else "")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_rpm"), env="conanrun")
