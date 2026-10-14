#!/usr/bin/env python3
"""Conan test_package for hpx/1.11.0 -- Conan L1 official test.

Builds a real HPX consumer program (test_hpx.cpp) and executes it with the
conanrun environment.  The program starts the HPX runtime and asserts the
results of real HPX tasks; it also carries the HarmonyOS specific end-to-end
assertions (R53).  On the Windows development host the OHOS binary cannot run;
there the test is only compiled and linked (tools.build:skip_test=True) and
the actual execution happens on HarmonyOS PC (W3/CI).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HpxTestConan(ConanFile):
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
        # Ninja places the executable directly in the (single-config) build
        # folder.
        test_binary = os.path.join(self.build_folder, "test_hpx")
        self.run(f"{test_binary} --hpx:threads=2", env="conanrun")
