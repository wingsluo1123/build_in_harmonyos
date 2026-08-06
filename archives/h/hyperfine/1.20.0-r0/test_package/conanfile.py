#!/usr/bin/env python3
"""Conan test_package — hyperfine 1.20.0-r0

R34: test_package must substantially exercise the tested package's functionality.
hyperfine is a CLI tool, so tests run the binary directly.

Tests:
  1. Verify binary exists in package (file existence check)
  2. Verify binary is an ELF file (format check)
  3. hyperfine --version (execution test — may fail on HarmonyOS due to
     libgcc_s.so.1 SELinux loading restriction, see notes.md)
"""
import os

from conan import ConanFile


class HyperfineTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
