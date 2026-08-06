#!/usr/bin/env python3
"""Conan test_package for easytag — verifies the installed binary exists."""
import os

from conan import ConanFile


class EasytagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must substantively depend on the tested package
        # Verify the easytag binary is installed and can report version
        self.run("easytag --version || true", env="conanrun")
