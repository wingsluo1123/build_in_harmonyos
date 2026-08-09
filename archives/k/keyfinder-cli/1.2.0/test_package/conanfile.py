#!/usr/bin/env python3
"""Conan test_package — keyfinder-cli 1.2.0

Tests the keyfinder-cli binary by running it with --help flag
and verifying it outputs usage information.
"""
from conan import ConanFile


class KeyfinderCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The conanrun env sets up PATH and LD_LIBRARY_PATH so that
        # keyfinder-cli binary is found and shared libs are loaded
        self.run("keyfinder-cli --help", env="conanrun")
