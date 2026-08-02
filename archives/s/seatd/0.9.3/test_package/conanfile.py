#!/usr/bin/env python3
"""Conan test_package for seatd 0.9.3 — L1 consumer test.

Builds a small C consumer that links against the packaged libseat and drives
the whole public API through the always-present ``noop`` backend
(``LIBSEAT_BACKEND=noop``), which needs neither a seatd daemon nor logind and
therefore works inside a CI container.

The test binary is launched through CTest only.  On HarmonyOS the default
/system/bin/sh (mksh) cannot exec the ELF directly, so CMake is told to invoke
the test through the shell reported by ``CONFIG_SHELL`` (empty everywhere
else).  Keeping that decision inside CMakeLists gives a single execution path
— no duplicated run, no hardcoded interpreter here.

File location: archives/s/seatd/0.9.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SeatdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Let CMakeLists decide how to launch the test binary.  Empty value =>
        # run it directly, which is what every normal Linux runner wants.
        tc.cache_variables["TEST_LAUNCHER"] = os.environ.get("CONFIG_SHELL", "")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Single execution path: CTest runs the binary (see CMakeLists.txt).
        cmake = CMake(self)
        cmake.test()
