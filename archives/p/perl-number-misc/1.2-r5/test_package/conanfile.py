#!/usr/bin/env python3
"""Conan test_package — perl-number-misc (Number::Misc) 1.2-r5

L1 test: verify the Perl module can be loaded and reports correct version.
"""
import os

from conan import ConanFile


class PerlnumbermiscTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed for a pure Perl module test
        pass

    def test(self):
        # Verify the module loads and reports the correct version
        self.run('perl -MNumber::Misc -e "print Number::Misc->VERSION, qq{\\n}"', env="conanrun")
