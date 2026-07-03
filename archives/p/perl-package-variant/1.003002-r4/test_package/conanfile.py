#!/usr/bin/env python3
"""Conan test_package — Package::Variant (pure Perl module).

Verifies that Package::Variant can be loaded by Perl.
"""
import os

from conan import ConanFile


class PerlPackageVariantTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Verify the Perl module can be loaded
        self.run("perl -e 'use Package::Variant; print \"Package::Variant loaded OK\\n\"'", env="conanrun")
