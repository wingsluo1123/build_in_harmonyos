#!/usr/bin/env python3
"""Conan test_package for teensy_loader_cli latest — Conan L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TeensyLoaderCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if can_run(self):
            dependency = self.dependencies["teensy_loader_cli"]
            binary = os.path.join(
                dependency.package_folder, "bin", "teensy_loader_cli")
            if not os.path.isfile(binary):
                raise RuntimeError(f"packaged executable is missing: {binary}")
            if not os.access(binary, os.X_OK):
                raise RuntimeError(f"packaged executable is not executable: {binary}")
            # Upstream 2.3 deliberately exits 1 after printing the MCU list.
            # Validate that exact contract instead of broadly ignoring errors.
            result = subprocess.run(
                [binary, "--list-mcus"], capture_output=True, text=True,
                check=False)
            output = result.stdout + result.stderr
            if result.returncode != 1:
                raise RuntimeError(
                    f"unexpected --list-mcus exit code {result.returncode}")
            expected = ("Supported MCUs are:", "atmega32u4", "at90usb1286")
            missing = [marker for marker in expected if marker not in output]
            if missing:
                raise RuntimeError(
                    f"--list-mcus output is missing markers: {missing}")
