#!/usr/bin/env python3
"""Smoke tests for the Swift OHOS toolchain package."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy


class SwiftToolchainTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if self.source_folder != self.build_folder:
            copy(self, "hello.swift", src=self.source_folder, dst=self.build_folder)

    def test(self):
        swift = shutil.which("swift")
        swiftc = shutil.which("swiftc")
        if not swift or not swiftc:
            raise RuntimeError("swift/swiftc not found on PATH from toolchain package")
        self.run(f'"{swift}" --version', env="conanrun")
        output = os.path.join(self.build_folder, "hello")
        self.run(f'"{swiftc}" "{os.path.join(self.build_folder, "hello.swift")}" -o "{output}"', env="conanbuild")
        self._sign_if_possible(output)
        self.run(f'"{output}"', env="conanrun")

    def _sign_if_possible(self, path):
        signer = shutil.which("binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy")
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
        if signer:
            self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
