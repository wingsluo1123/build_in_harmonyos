#!/usr/bin/env python3
"""Conan test_package for breeze-icons5 5.116.0 (data-only icon theme).

A data-only package ships no libraries/binaries to link or execute, so the
test() method runs a standalone consumer validation program (test_package.py)
that verifies the installed Breeze theme is complete and discoverable:
breeze and breeze-dark index.theme, a representative icon, and non-trivial icon
counts (incl. dark-theme light fallbacks).
"""
import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    win_bash = True
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_package.py")
        self.run(f'"{sys.executable}" "{script}" "{dep.package_folder}"')
