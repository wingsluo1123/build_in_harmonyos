#!/usr/bin/env python3
"""Conan test_package for abcselect 1.5.

abcselect is a Perl script tool — the test verifies the script exists
and responds to --help.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AbcselectTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abcselect"]
        bindir = os.path.join(dep.package_folder, "bin")
        abcselect = os.path.join(bindir, "abcselect")

        if not os.path.isfile(abcselect):
            raise ConanException(f"abcselect not found: {abcselect}")

        self.output.info(f"  abcselect: {os.path.getsize(abcselect)} bytes")

        # Run --help to verify the script works
        result = self.run(f"{abcselect} --help 2>&1", env="conanrun", ignore_errors=True)
        if result >= 128 or result == 127:
            raise ConanException(f"abcselect crashed (exit code {result})")
        if result != 0:
            raise ConanException(f"abcselect --help failed (exit code {result})")
        self.output.info("abcselect --help: OK")