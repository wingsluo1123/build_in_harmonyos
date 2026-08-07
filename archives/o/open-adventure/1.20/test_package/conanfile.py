#!/usr/bin/env python3
"""Conan test_package for open-adventure 1.20.

Compiles and runs a test program that verifies the advent binary
exists and produces the expected welcome message.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class OpenAdventureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy test source
        copy(self, "test.c", self.source_folder, self.build_folder)

        # Compile the test program
        cc = "clang"
        self.run(f"{cc} -std=c99 -o test_advent test.c")

    def test(self):
        # Run the test program — it will find and execute advent
        self.run("./test_advent", env="conanrun")
