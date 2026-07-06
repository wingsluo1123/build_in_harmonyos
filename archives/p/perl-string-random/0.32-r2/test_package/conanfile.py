#!/usr/bin/env python3
"""Conan test_package — perl-string-random 0.32-r2 (pure Perl module).

Verifies that String::Random can be loaded and used to generate
random strings from a pattern.
"""
import os

from conan import ConanFile


class PerlStringRandomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency
        deps = self.dependencies["perl-string-random"]
        pkg_folder = deps.package_folder
        # The module is installed under data/service/hnp/perl.org/.../site_perl/...
        perl_lib = os.path.join(pkg_folder, "data", "service", "hnp",
                                "perl.org", "perl_5.42.0", "lib",
                                "site_perl", "5.42.0")
        # Write test script to temp file
        test_script = r'''use strict;
use warnings;
use String::Random;

my $sr = String::Random->new();
my $s = $sr->randpattern("Ccnc");
die "too short" unless length($s) == 4;
print "OK: String::Random version $String::Random::VERSION works\n";
'''
        test_file = os.path.join(self.build_folder, "test_string_random.pl")
        with open(test_file, "w") as f:
            f.write(test_script)

        # Run with PERL5LIB set
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib, test_file))
