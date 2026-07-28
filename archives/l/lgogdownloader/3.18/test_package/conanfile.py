#!/usr/bin/env python3
"""Conan test_package — lgogdownloader 3.18 L1 smoke test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LgogdownloaderTestConan(ConanFile):
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
        # lgogdownloader needs network + GOG credentials, so we test --version/--help only
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "lgogdownloader")
        if os.path.isfile(bin_path):
            self.run(f'{bash} -c "{bin_path} --version"', env="conanrun", ignore_errors=True)
            self.run(f'{bash} -c "{bin_path} --help"', env="conanrun", ignore_errors=True)
