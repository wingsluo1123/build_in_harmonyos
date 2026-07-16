#!/usr/bin/env python3
"""Conan test_package for fmt/11.2.0-r1 — consumer-side validation.

R34: Substantially depends on the tested package.
The test source (test.cpp) calls fmt::format, fmt::print, fmt::to_string.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class FmtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

        # Fix compiler path: CI profile may point to a path that doesn't
        # exist on the local build machine.
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            replaced = False
            clang_path = shutil.which("clang")
            clangxx_path = shutil.which("clang++")
            if clang_path and "/data/service/hnp/bin/clang" in content:
                content = content.replace("/data/service/hnp/bin/clang", clang_path)
                replaced = True
            if clangxx_path and "/data/service/hnp/bin/clang++" in content:
                content = content.replace("/data/service/hnp/bin/clang++", clangxx_path)
                replaced = True
            if replaced:
                with open(toolchain_file, "w") as f:
                    f.write(content)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (L0d requires self.run() call)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_fmt")
        self.run(test_bin, env="conanrun")
