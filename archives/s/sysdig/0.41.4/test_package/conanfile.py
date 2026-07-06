#!/usr/bin/env python3
"""Conan test_package — sysdig 0.41.4 (CLI tool).

L1 test: run sysdig --version to verify the built binary works
on the target platform.
"""
import os
import subprocess

from conan import ConanFile


class SysdigTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step — sysdig is a prebuilt binary

    def test(self):
        dep = self.dependencies["sysdig"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        sysdig = os.path.join(bin_dir, "sysdig")

        # self.run() checks exit code; sysdig --version returns 0
        # Redirect stderr to stdout to capture version output
        output = self.run(f"{sysdig} --version 2>&1", env="conanrun", output=True)
        assert "0.41.4" in output, f"Expected '0.41.4' in sysdig output, got: {output[:200]}"
        self.output.info("✅ sysdig --version passed — version 0.41.4")
