#!/usr/bin/env python3
"""Conan test_package — bvi 1.5.0 smoke test.

bvi is a terminal-based binary editor; it requires a PTY to run.
We verify the binary exists and is executable.
"""
import os

from conan import ConanFile


class BviTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["bvi"]
        bvi_bin = os.path.join(dep.package_folder, "bin", "bvi")
        # bvi is a terminal editor (ncurses); --version fails without a PTY.
        # Smoke test: verify binary exists and is executable.
        self.run(f'test -x "{bvi_bin}"', env="conanrun")
