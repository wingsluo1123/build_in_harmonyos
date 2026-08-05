#!/usr/bin/env python3
"""Test package for libid3tag (cross-compiled to OHOS).

This test creates an ID3 tag, adds a title frame, renders it,
parses it back, and verifies the content.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libid3tagTestConan(ConanFile):
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
        # Set LD_LIBRARY_PATH for shared lib on OHOS/Linux
        libid3tag_dep = self.dependencies["libid3tag"]
        libdir = os.path.join(libid3tag_dep.package_folder, "lib")
        existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            f"{libdir}:{existing_ld}" if existing_ld else libdir
        )
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(test_bin, env="conanrun")
