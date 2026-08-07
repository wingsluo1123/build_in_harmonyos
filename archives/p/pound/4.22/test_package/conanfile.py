#!/usr/bin/env python3
"""Conan test_package — pound 4.22 (application test).

Verifies the pound binary works by running `pound -V`.
"""
import os

from conan import ConanFile


class PoundTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run pound -V to verify the binary works
        # VirtualRunEnv adds the pound bin/ to PATH
        self.run("pound -V", env="conanrun")
