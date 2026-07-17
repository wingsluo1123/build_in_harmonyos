#!/usr/bin/env python3
"""Conan test_package for asymptote 3.12 — verify the installed executable.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

asymptote is a terminal tool (`asy` vector graphics compiler); the test
runs a small consumer program to verify the package is consumable, plus
invokes `asy --version` tolerating non-zero exit (asy prints version then
exits non-zero when TeX is absent).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class AsymptoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dependency = self.dependencies["asymptote"]
            binary = os.path.join(dependency.package_folder, "bin", "asy")
            if not os.path.isfile(binary):
                raise RuntimeError(f"packaged executable is missing: {binary}")
            if not os.access(binary, os.X_OK):
                raise RuntimeError(f"packaged executable is not executable: {binary}")
            result = subprocess.run(
                [binary, "--version"], capture_output=True, text=True,
                check=False)
            output = result.stdout + result.stderr
            if result.returncode not in (0, 1):
                raise RuntimeError(
                    f"unexpected asy --version exit code {result.returncode}")
            if "Asymptote" not in output or "3.12" not in output:
                raise RuntimeError("asy --version did not report version 3.12")
