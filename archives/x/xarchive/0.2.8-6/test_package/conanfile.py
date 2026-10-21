#!/usr/bin/env python3
"""Conan test package for xarchive 0.2.8-6."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class XarchiveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        pkg = self.dependencies["xarchive"].package_folder
        bin_path = os.path.join(pkg, "bin", "xarchive")
        if not os.path.isfile(bin_path):
            raise ConanException(f"xarchive binary missing: {bin_path}")

        smoke = os.path.join(os.path.dirname(__file__), "test_xarchive.py")
        if not can_run(self):
            self.output.info("Runnable smoke skipped on this target")
            return

        self.run(f'"{sys.executable}" "{smoke}" "{bin_path}"', env="conanrun")
