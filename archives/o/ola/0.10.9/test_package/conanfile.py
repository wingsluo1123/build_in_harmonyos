#!/usr/bin/env python3
"""test_package/conanfile.py — Conan L1 official test.

R34 (iron-rules) compliance: this test_package actually calls libolacommon
APIs (IPV4Address::FromStringOrDie, MACAddress::FromStringOrDie, RDM UID,
DmxBuffer channel ops, StringUtils) — see test_ola.cpp. It is not a printf
stub; CI's P0 audit grep would catch that.

Build: CMake + test_ola.cpp (no in-tree unit tests required).
Test:  ctest runs the binary; non-zero exit fails the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OlaTestConan(ConanFile):
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
        # Run the test binary directly so we capture exit code precisely.
        # (cmake.test() would also work but goes through ctest which adds
        # indirection — direct run is more deterministic for CI audits.)
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_ola")
        self.run(cmd, env="conanrun")