#!/usr/bin/env python3
"""Conan test_package for stk/latest — L1 consumer test.

Builds a small C++ consumer against the packaged libstk and exercises the
DSP core (oscillator, noise source, one-pole/one-zero filters, delay line,
ADSR envelope) plus the Thread/Mutex classes touched by this archive's
portability patches.

Linking against Thread.h/Mutex.h also verifies that the recipe propagates
STK's __OS_LINUX__ switch to consumers: without it those headers do not
declare THREAD_HANDLE/MUTEX and this test would not compile.

The test binary is launched through CTest only.  On HarmonyOS the default
/system/bin/sh (mksh) cannot exec the ELF directly, so CMake is told to
invoke the test through the shell reported by ``CONFIG_SHELL`` (empty
everywhere else).  Keeping that decision inside CMakeLists gives a single
execution path — no duplicated run, no hardcoded interpreter here.

File location: archives/s/stk/latest/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class StkTestConan(ConanFile):
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
