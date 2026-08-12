#!/usr/bin/env python3
"""Conan test_package — Gauche 0.9.15.

Runs the gosh interpreter to verify it can evaluate Scheme expressions.
This is the L1 test in the five-level test system.

File location: archives/g/gauche/0.9.15.1/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GaucheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        # headers=True, libs=True: test_package compiles test.c against
        # gauche.h and links libgauche, so it needs the full compile-time
        # info (include dirs + libs).  Without these traits Conan 2.29
        # defaults test requires to headers=False/libs=False, which makes
        # CMakeDeps emit empty INCLUDE_DIRS/LIBS and the test build fails
        # with "'gauche.h' file not found".
        self.requires(self.tested_reference_str, headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()

        # Also run gosh directly to verify the interpreter works
        bin_dir = os.path.join(self.cpp.build.bindirs[0])
        gosh_path = os.path.join(bin_dir, "gosh")
        if os.path.isfile(gosh_path):
            self.run(f'"{gosh_path}" -e "(display (+ 1 2 3))(newline)"', env="conanrun")
