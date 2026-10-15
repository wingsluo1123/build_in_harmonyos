#!/usr/bin/env python3
"""Conan test_package for sokol 0.0-git.2e75443 — Conan L1 consumer test.

Consumer-perspective verification against the packaged headers (no
conan create-side cache):
  - test_sokol.c   (C99)  : 54 assertions across 11 core/util headers
    (dummy-backend setup/shutdown lifecycles, args parsing, time math,
    fetch real-file async load, color/shape math, letterbox viewport,
    memtrack alloc/free, log smoke, framebuffer lifecycle)
  - test_sokol.cc  (C++11): sokol_cmdbuf implementation section
    compiled as C++ (upstream compile-suite contract, patch s0001)

All assertion anchors were calibrated on the target (OHOS aarch64,
clang 15, musl) during recipe bring-up.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SokolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # run both consumer TUs via CTest
        cmake.test()
        # also run directly for L1b log evidence
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sokol_c"),
                 env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sokol_cxx"),
                 env="conanrun")
