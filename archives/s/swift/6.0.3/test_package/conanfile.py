#!/usr/bin/env python3
"""Smoke tests for the Swift OHOS toolchain package."""
import os

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
        self.run("swift --version", env="conanrun")
        output = os.path.join(self.build_folder, "hello")
        self.run(f'swiftc "{os.path.join(self.build_folder, "hello.swift")}" -o "{output}"', env="conanbuild")
        self._sign_if_possible(output)
        self.run(f'"{output}"', env="conanrun")

    def _sign_if_possible(self, path):
        self.run(
            f'if command -v llvm-objcopy >/dev/null 2>&1; then '
            f'llvm-objcopy --remove-section .codesign "{path}" || true; fi',
            env="conanbuild",
        )
        self.run(
            f'if command -v binary-sign-tool >/dev/null 2>&1; then '
            f'binary-sign-tool sign -inFile "{path}" -outFile "{path}" -selfSign 1; fi',
            env="conanbuild",
        )
