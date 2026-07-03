#!/usr/bin/env python3
"""Conan test_package — perl-params-validate 1.31.

L1 test: verify the Perl module can be loaded and used.
"""
import os

from conan import ConanFile
from conan.tools.files import save


class PerlParamsValidateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Write a simple test script
        test_code = """use strict;
use warnings;
use Params::Validate qw(validate validate_pos);
print "Params::Validate version: ", Params::Validate->VERSION, "\\n";
print "TEST OK\\n";
"""
        save(self, os.path.join(self.source_folder, "test.pl"), test_code)

    def test(self):
        # Run the Perl test script
        self.run("perl " + os.path.join(self.source_folder, "test.pl"), env="conanrun")
