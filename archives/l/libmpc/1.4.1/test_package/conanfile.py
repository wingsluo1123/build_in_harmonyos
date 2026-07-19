#!/usr/bin/env python3
"""Conan test_package — Consumer test for libmpc 1.4.1.

This test substantively depends on the libmpc package by calling
its core API (mpc_init2, mpc_set_ui_ui, mpc_add, mpc_cmp_si_si).
R34: test must depend on the tested package.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibmpcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # Patch generated CMake toolchain to fix CI-specific compiler paths
        # that don't exist on the build machine.
        gen_dir = Path(self.generators_folder)
        for cmake_file in gen_dir.glob("conan_toolchain*.cmake"):
            content = cmake_file.read_text(encoding="utf-8")
            content = content.replace(
                "/data/service/hnp/bin/clang",
                "/storage/Users/currentUser/usr/local/bin/clang"
            )
            content = content.replace(
                "/data/service/hnp/bin/clang++",
                "/storage/Users/currentUser/usr/local/bin/clang++"
            )
            cmake_file.write_text(content, encoding="utf-8")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libmpc")
        self.run(test_bin, env="conanrun")
