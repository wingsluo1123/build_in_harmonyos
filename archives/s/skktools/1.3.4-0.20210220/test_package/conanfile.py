#!/usr/bin/env python3
"""Conan test_package driver for skktools 1.3.4-0.20210220.

Runs test_skktools.py against the packaged bin/ directory.
"""
import os
import sys

from conan import ConanFile


class SkktoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["skktools"].package_folder, "bin")
        script = os.path.join(os.path.dirname(__file__), "test_skktools.py")
        self.run('"%s" "%s" "%s"' % (sys.executable, script, bin_dir),
                 env="conanrun")
