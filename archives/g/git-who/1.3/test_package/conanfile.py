#!/usr/bin/env python3
"""Conan test_package — git-who 1.3 smoke test.

Compiles test_git_who with CMake to satisfy L0 no_test_sources gate,
then runs the binary to verify git-who --help works.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class GitWhoTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
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
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        bin_path = os.path.join(self.dependencies["git-who"].package_folder,
                                "bin", "git-who")
        if not os.path.exists(bin_path):
            raise Exception(f"git-who binary not found: {bin_path}")
        # Run the compiled test binary (verifies git-who --help)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_git_who")
        self.run(f'"{test_bin}"', env="conanrun")
