#!/usr/bin/env python3
"""Conan test_package for libkcapi 1.5.0 — L1 consumer test.

Builds a small C consumer that links against the packaged libkcapi and
exercises the version APIs plus the AF_ALG message-digest path, which is the
code touched by ``patches/0001-lib-kcapi-kernel-if.c.patch``.

The test binary is launched through CTest only.  On HarmonyOS the default
/system/bin/sh (mksh) cannot exec the ELF directly, so CMake is told to invoke
the test through the shell reported by ``CONFIG_SHELL`` (empty everywhere
else).  Keeping that decision inside CMakeLists gives a single execution path
— no duplicated run, no hardcoded interpreter here.

File location: archives/l/libkcapi/1.5.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibkcapiTestConan(ConanFile):
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
