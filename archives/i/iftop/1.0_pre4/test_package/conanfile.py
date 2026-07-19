#!/usr/bin/env python3
"""Conan runtime test for the installed iftop executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class IftopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script}"', env="conanrun")
