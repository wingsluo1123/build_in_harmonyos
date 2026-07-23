#!/usr/bin/env python3
"""Conan test_package for mutt 2.2.16 — L1 smoke test.

Runs `mutt -v` to verify the binary is functional.
R34: test must actually exercise the tested package's binary.
"""
from conan import ConanFile


class MuttTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("mutt -v", env="conanrun")
