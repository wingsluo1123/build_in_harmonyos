#!/usr/bin/env python3
"""Conan test_package for isync 1.5.1.

isync is a command-line tool (mbsync), not a library.
This test verifies the installed binary works by running `mbsync --version`.
"""
import os

from conan import ConanFile


class IsyncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must substantively use the tested package
        # Run mbsync --version to verify the binary is functional
        self.run("mbsync --version", env="conanrun")
