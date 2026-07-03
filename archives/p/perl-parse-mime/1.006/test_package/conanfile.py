#!/usr/bin/env python3
"""Conan test_package for perl-parse-mime — Perl L1 test.

Tests that the installed Parse::MIME module can be loaded and used.
"""
from conan import ConanFile


class PerlparsemimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use Parse::MIME qw( best_match ); '
            'my $m = best_match( [ qw( application/xbel+xml text/xml ) ], '
            '\'text/*;q=0.5,*/*; q=0.1\' ); '
            'die "test failed" unless $m eq "text/xml"; '
            'print "Parse::MIME test OK\\n";'
        )
        self.run(f'perl -e \'{test_script}\'')
