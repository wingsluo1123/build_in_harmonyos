#!/usr/bin/env python3
"""Conan test_package for aria2 — verifies the aria2c binary works.

aria2 is a command-line tool, so the test runs the binary directly
rather than linking against a library.
"""
import os

from conan import ConanFile


class Aria2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run aria2c --version and verify output
        self.run("aria2c --version", env="conanrun")
