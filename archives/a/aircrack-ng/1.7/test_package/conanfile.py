#!/usr/bin/env python3
"""Conan test_package — aircrack-ng 1.7

R34: test_package must substantially exercise the tested package's functionality.
aircrack-ng is a set of command-line tools, so tests run binaries directly.

Tests:
  1. aircrack-ng --help  — verify main binary is installed and runnable
  2. makeivs-ng --help   — verify makeivs-ng binary works
  3. command -v kstats    — verify kstats binary is installed and on PATH
"""

from conan import ConanFile


class AircrackNgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: aircrack-ng --help (main binary smoke test)
        self.run("aircrack-ng --help", env="conanrun")

        # Test 2: makeivs-ng --help (IVS file generator)
        self.run("makeivs-ng --help", env="conanrun")

        # Test 3: Verify kstats binary is installed and on PATH
        self.run("command -v kstats", env="conanrun")
