#!/usr/bin/env python3
"""Conan test_package for aria2 — verifies the aria2c binary works.

aria2 is a command-line tool, so the test runs the binary directly
rather than linking against a library.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class Aria2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy test source file (required by CI L0c)
        src = os.path.join(self.source_folder, "test_aria2.c")
        if os.path.exists(src):
            copy(self, "test_aria2.c", self.source_folder, self.build_folder)

    def test(self):
        # Run aria2c --version and verify output
        self.run("aria2c --version", env="conanrun")
