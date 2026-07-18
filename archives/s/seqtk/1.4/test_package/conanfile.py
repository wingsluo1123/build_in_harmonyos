#!/usr/bin/env python3
"""Conan test package for seqtk 1.4."""

import os

from conan import ConanFile


class SeqtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_seqtk.sh")
        shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f'"{shell}" "{script}"', env="conanrun")
