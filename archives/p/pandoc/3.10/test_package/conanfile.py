#!/usr/bin/env python3
"""Conan test_package — pandoc (executable tool).

pandoc is a command-line tool. Test: run `pandoc --version`.
"""
import os

from conan import ConanFile


class PandocTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Smoke test: verify pandoc executable runs and reports version
        self.run("pandoc --version", env="conanrun")
