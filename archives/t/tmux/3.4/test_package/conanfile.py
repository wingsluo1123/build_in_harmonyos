#!/usr/bin/env python3
"""Conan test_package — tmux 3.4

L1 test: verify the tmux binary is functional.
"""
import os

from conan import ConanFile


class TmuxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify tmux binary is functional
        bin_path = os.path.join(self.cpp_info.bindirs[0], "tmux")
        self.run(f'"{bin_path}" -V', env="conanrun")
