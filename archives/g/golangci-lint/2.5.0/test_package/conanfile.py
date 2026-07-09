#!/usr/bin/env python3
"""Conan test_package for golangci-lint 2.5.0 — L1 smoke test.

Tests that the golangci-lint binary can be executed and reports its version.
On HarmonyOS, static Go binaries require the ELF loader to run.
"""
import os

from conan import ConanFile


class GolangciLintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the golangci-lint binary in the package
        bin_path = os.path.join(self.dependencies["golangci-lint"].package_folder, "bin", "golangci-lint")
        self.output.info(f"Testing golangci-lint binary at: {bin_path}")
        # On HarmonyOS, use elfldr to run static Go binaries
        elfldr = os.path.expanduser("~/tmp/elfldr")
        if os.path.exists(elfldr):
            self.run(f'"{elfldr}" "{bin_path}" --version', env="conanrun")
        else:
            self.run(f'"{bin_path}" --version', env="conanrun")
