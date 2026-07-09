#!/usr/bin/env python3
"""Conan test_package for libzippp — L1 official test.

验证 libzippp 包可以被发现、链接和运行时可用。
CI 通过 conan create 自动执行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibzipppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution (R5: OHOS has no /bin/sh).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_libzippp'", env="conanrun")
