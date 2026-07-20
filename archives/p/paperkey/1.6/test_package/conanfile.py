#!/usr/bin/env python3
"""Conan test_package — paperkey 1.6

Tests the paperkey binary by running --version.
paperkey is a command-line tool, not a library, so we test the binary directly.
"""
import os

from conan import ConanFile


class PaperkeyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = self.dependencies["paperkey"].cpp_info.bindirs[0]
        paperkey_bin = os.path.join(bin_dir, "paperkey")
        self.run(f'"{paperkey_bin}" --version', env="conanrun")
