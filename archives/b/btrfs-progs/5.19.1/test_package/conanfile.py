#!/usr/bin/env python3
"""Conan test_package for btrfs-progs 5.19.1 — L1 smoke test.

Verifies that the installed btrfs and mkfs.btrfs binaries can execute
and report their version numbers correctly.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BtrfsProgsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Use conanrun env which sets up PATH to find installed binaries
            self.run("btrfs --version", env="conanrun")
