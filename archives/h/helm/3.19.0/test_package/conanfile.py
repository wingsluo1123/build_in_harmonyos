#!/usr/bin/env python3
"""Conan test_package for helm 3.19.0 — L1 smoke test.

Tests that the helm binary can be executed and reports its version.
On HarmonyOS, static Go binaries require the ELF loader to run.
"""
import os

from conan import ConanFile


class HelmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the helm binary in the package
        helm_bin = os.path.join(self.dependencies["helm"].package_folder, "bin", "helm")
        self.output.info(f"Testing helm binary at: {helm_bin}")
        # On HarmonyOS, use elfldr to run static Go binaries
        elfldr = os.path.expanduser("~/tmp/elfldr")
        if os.path.exists(elfldr):
            self.run(f'"{elfldr}" "{helm_bin}" version', env="conanrun")
        else:
            self.run(f'"{helm_bin}" version', env="conanrun")
