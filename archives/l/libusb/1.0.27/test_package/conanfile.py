#!/usr/bin/env python3
"""Conan test_package for libusb 1.0.27 — L1 official test.

Builds a small C consumer that links against the packaged libusb-1.0 and
exercises the version / error-string APIs plus the OHOS-supported
initialisation path.

File location: archives/l/libusb/1.0.27/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibusbTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the invocation in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_package'", env="conanrun")
