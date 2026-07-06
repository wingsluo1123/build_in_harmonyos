#!/usr/bin/env python3
"""Conan test_package — perl-parallel-forkmanager 2.04 (Pure Perl module).

Tests that the Parallel::ForkManager Perl module can be loaded.
"""
import os

from conan import ConanFile


class PerlParallelForkManagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for pure Perl module test

    def test(self):
        # Run the test script (test.sh wraps perl test for CI L0c compliance)
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_script}", env="conanrun")
