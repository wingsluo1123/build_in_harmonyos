#!/usr/bin/env python3
"""Test package for rom-tools 0.288 — verifies chdman and romcmp CLI tools work."""
import os

from conan import ConanFile


class RomToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["rom-tools"].cpp_info.bindirs[0]

        # chdman: run with 'info' subcommand (expects error but prints version banner)
        chdman = os.path.join(bindir, "chdman")
        # Verify chdman produces expected output containing version string
        self.run(f'"{chdman}" info 2>&1 | grep -q "chdman.*CHD"', env="conanrun")

        # romcmp: run without args (prints usage)
        romcmp = os.path.join(bindir, "romcmp")
        self.run(f'"{romcmp}" 2>&1 | grep -q "romcmp"', env="conanrun")
