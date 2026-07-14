#!/usr/bin/env python3
"""Conan test_package for httping — L1 smoke test.

Verifies httping binary is installed and runs --version/--help successfully.
"""
from pathlib import Path

from conan import ConanFile


class HttpingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = Path(self.source_folder) / "test.sh"
        self.run(f"sh {script}", env="conanrun")
