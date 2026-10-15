#!/usr/bin/env python3
"""Conan test_package for libxtrxdsp — Conan L1 official test.

File location:
  archives/l/libxtrxdsp/0.0.1-git20230203.271f5e6/test_package/conanfile.py

Compiles two consumer programs against the *installed* package and runs them:

  * test_consumer.c  — public API surface: float<->int16 sample conversion
                       (interleaving, de-interleaving, truncation, scaling,
                       block and tail paths) and the FIR channel filter
                       (parameter validation, documented return value, all-pass
                       pass-through with a 1-tap filter).
  * test_ohos_dsp.c  — HarmonyOS-specific properties of this adaptation: the
                       packaged symbol set, the aarch64 generic code path,
                       little-endian lane order and filter allocation cycles.

Both programs link libxtrxdsp and call its public symbols, so the CI L1e
destructive reverse check (moving lib/ or include/ away) makes this test fail.
"""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

import os


class LibxtrxdspTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."

        # Consumer integration test: conversions + FIR channel filter.
        self.run(os.path.join(bindir, "test_consumer"), env="conanrun")

        # HarmonyOS-specific test: symbol set / code path / byte order.
        self.run(os.path.join(bindir, "test_ohos_dsp"), env="conanrun")
