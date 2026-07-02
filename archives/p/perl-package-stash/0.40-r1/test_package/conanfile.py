#!/usr/bin/env python3
"""Conan test_package for perl-package-stash — L1 smoke test.

Verifies that Package::Stash can be loaded and used after installation.
"""
import os

from conan import ConanFile


class PerlPackageStashTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Smoke test: load Package::Stash module
        # -M flag loads the module; -e1 runs trivial expression
        # If module loads, exit 0; otherwise non-zero
        self.run("perl -MPackage::Stash -e1", env="conanrun")
