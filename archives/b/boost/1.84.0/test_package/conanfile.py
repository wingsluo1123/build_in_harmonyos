#!/usr/bin/env python3
"""Real consumer test for the two compiled Boost components."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostTestConan(ConanFile):
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
        binary = os.path.join(self.build_folder, "boost_components_test")
        if not os.path.isfile(binary):
            binary = os.path.join(self.build_folder, "Release", "boost_components_test")
        assert os.path.isfile(binary), f"test binary not found: {binary}"
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shlex.quote(shell)} -c {shlex.quote(binary)}", env="conanrun")
