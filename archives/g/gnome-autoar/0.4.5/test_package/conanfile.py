#!/usr/bin/env python3
"""Conan test_package — gnome-autoar 0.4.5

L1 test: calls autoar_libarchive_quark() and autoar_format_is_valid()
to verify the library is correctly built and linked.

Static build is used to avoid E088 (HarmonyOS musl namespace isolation).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GnomeAutoarTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly to verify runtime behavior
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gnome_autoar")
        if os.path.isfile(exe):
            self.run(exe, env="conanrun")
