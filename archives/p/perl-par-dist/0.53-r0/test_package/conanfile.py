#!/usr/bin/env python3
"""Conan test_package for perl-par-dist — Perl L1 test.

Tests that the installed PAR::Dist module can be loaded and used.
"""
from conan import ConanFile


class PerlpardistTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use PAR::Dist; '
            'my $dist = PAR::Dist::parse_dist_name("PAR-Dist-0.53-i386-freebsd-5.8.0.par"); '
            'die "test failed: name parse" unless defined $dist; '
            'print "PAR::Dist test OK\\n";'
        )
        self.run(f'perl -e \'{test_script}\'')
