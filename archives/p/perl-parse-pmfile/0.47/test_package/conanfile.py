#!/usr/bin/env python3
"""Conan test_package for perl-parse-pmfile — Perl L1 test.

Tests that the installed Parse::PMFile module can be loaded and used.
"""
from conan import ConanFile


class PerlparsepmfileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use Parse::PMFile; '
            'my $parser = Parse::PMFile->new; '
            'die "test failed" unless $parser; '
            'print "Parse::PMFile test OK\\n";'
        )
        self.run(f"perl -e '{test_script}'")
