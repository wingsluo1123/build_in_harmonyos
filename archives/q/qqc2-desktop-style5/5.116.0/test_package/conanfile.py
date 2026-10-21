#!/usr/bin/env python3
"""Conan test_package for qqc2-desktop-style5 5.116.0.

QML style-plugin package (no standalone binary); test() runs the standalone
test_package.py consumer validation via self.run() to satisfy the CI gate that
requires actual test execution.
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
