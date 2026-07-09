#!/usr/bin/env python3
"""Conan test_package for actionlint 1.7.9 — L1 smoke test.

Tests that the actionlint binary can be executed and reports its version.
On HarmonyOS, static Go binaries require the ELF loader to run.
"""
import os

from conan import ConanFile


class ActionlintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the actionlint binary in the package
        actionlint_bin = os.path.join(self.dependencies["actionlint"].package_folder, "bin", "actionlint")
        self.output.info(f"Testing actionlint binary at: {actionlint_bin}")
        # On HarmonyOS, use elfldr to run static Go binaries
        elfldr = os.path.expanduser("~/tmp/elfldr")
        if os.path.exists(elfldr):
            self.run(f'"{elfldr}" "{actionlint_bin}" --version', env="conanrun")
        else:
            self.run(f'"{actionlint_bin}" --version', env="conanrun")
