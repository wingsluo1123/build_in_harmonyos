#!/usr/bin/env python3
"""Test package for pure-ftpd — verifies the FTP daemon binary is functional."""
import os

from conan import ConanFile


class PureFtpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify pure-ftpd binary runs and shows help
        self.run("pure-ftpd --help", env="conanrun")
        # Verify pure-pw binary runs
        self.run("pure-pw --help", env="conanrun")
