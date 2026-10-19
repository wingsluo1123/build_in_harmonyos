#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libdispatch/{version}/test_package/conanfile.py
"""
import os
from pathlib import Path
import shutil
import stat

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdispatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        binary = Path(self.build_folder) / "test_libdispatch"
        if self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise RuntimeError("binary-sign-tool is required for OHOS consumer execution")
            signed = binary.with_name(binary.name + ".signed")
            if signed.exists():
                raise RuntimeError("Unexpected signature output already exists")
            self.run(f'"{signer}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1')
            signed.chmod(stat.S_IMODE(binary.stat().st_mode))
            signed.replace(binary)
        self.run(f'"{binary}"', env="conanrun", cwd=self.build_folder)
