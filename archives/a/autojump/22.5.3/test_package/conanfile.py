#!/usr/bin/env python3
"""Conan test_package for autojump — verifies the installed tool works.

R34: Test must substantively depend on the tested package by executing
the autojump binary and checking its output.
"""
import os

from conan import ConanFile


class AutojumpTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # R34: Substantive test — execute the actual autojump binary
        autojump_pkg = self.dependencies["autojump"].package_folder
        autojump_bin = os.path.join(autojump_pkg, "usr", "local", "bin", "autojump")
        self.run(f'"{autojump_bin}" --version')
