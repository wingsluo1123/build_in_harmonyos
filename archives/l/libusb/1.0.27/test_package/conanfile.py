#!/usr/bin/env python3
"""Conan test_package for libusb 1.0.27 — L1 official test.

Builds a small C consumer that links against the packaged libusb-1.0 and
exercises the version / error-string APIs plus the initialisation path that
is supported inside the HarmonyOS sandbox.

The test binary is launched through CTest only.  On HarmonyOS the default
/system/bin/sh (mksh) cannot exec the ELF directly, so CMake is told to
invoke the test through the shell reported by ``CONFIG_SHELL`` (falling back
to whatever ``bash`` is on PATH).  Doing it inside CMakeLists keeps a single
execution path — no duplicated run, no hardcoded interpreter here.

File location: archives/l/libusb/1.0.27/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibusbTestConan(ConanFile):
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
        # Single execution path: CTest launches the binary exactly once, using
        # the TEST_LAUNCHER wiring in CMakeLists.txt.  Invoking ctest through
        # self.run() (instead of cmake.test()) is required by the CI gate
        # ci/conan/build_and_test.sh L0d, which greps this file for self.run.
        self.run("ctest --output-on-failure", cwd=self.build_folder,
                 env="conanrun")
