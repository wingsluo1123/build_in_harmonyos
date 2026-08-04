#!/usr/bin/env python3
"""Conan consumer test for aqua v2.60.0."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AquaTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_aqua.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["aqua"].package_folder
        exe = os.path.join(package_folder, "bin", "aqua")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing aqua executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_aqua.py")
        self.run(f'"{sys.executable}" "{script}" "{exe}"', env="conanrun")
