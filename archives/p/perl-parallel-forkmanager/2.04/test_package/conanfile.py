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
        # Test that the Perl module can be loaded
        self.run('perl -MParallel::ForkManager -e "print qq(Parallel::ForkManager loaded OK\\n)"', env="conanrun")
