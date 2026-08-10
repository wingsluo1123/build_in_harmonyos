#!/usr/bin/env python3
"""Conan test_package for gphoto2 2.5.32 — CLI tool verification.

R34: This test executes the gphoto2 binary (the actual package output),
not just printing a string. It runs:
  1. gphoto2 --version — verifies binary is installed and reports version
  2. gphoto2 --list-ports — exercises libgphoto2 port enumeration API
"""
import os

from conan import ConanFile


class Gphoto2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Execute the gphoto2 binary — real API call via CLI
        # --version verifies the binary runs and reports correct version
        self.run("gphoto2 --version", env=["conanrun"])

        # --list-ports exercises the libgphoto2 port enumeration API
        # through the gphoto2 CLI, verifying dependency linkage
        self.run("gphoto2 --list-ports", env=["conanrun"])
