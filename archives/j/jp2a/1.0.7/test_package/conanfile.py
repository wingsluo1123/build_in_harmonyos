#!/usr/bin/env python3
"""Conan test_package for jp2a 1.0.7 — CLI tool smoke test.

jp2a is a command-line tool (not a library), so we just verify
that the binary runs and reports its version.
"""
import os

from conan import ConanFile


class Jp2ATestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed, just test the installed binary
        pass

    def test(self):
        # Verify the binary exists and runs
        self.run("jp2a --version", env="conanrun", ignore_errors=False)
