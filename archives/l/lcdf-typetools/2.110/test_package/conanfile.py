#!/usr/bin/env python3
"""Conan test_package for lcdf-typetools 2.110.

Verifies that all 11 installed tools are accessible and report the
correct version string containing "2.110".
"""
from conan import ConanFile


class LcdftypetoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # All 11 tools provided by lcdf-typetools
        tools = [
            "cfftot1", "mmafm", "mmpfb", "otfinfo", "otftotfm",
            "t1dotlessj", "t1lint", "t1rawafm", "t1reencode",
            "t1testpage", "ttftotype42",
        ]
        for tool in tools:
            # Run each tool with --version and verify output contains "2.110"
            # grep exits with 1 if pattern not found, failing the test
            self.run(f'{tool} --version 2>&1 | grep "2.110"', env="conanrun")
