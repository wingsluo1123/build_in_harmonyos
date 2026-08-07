#!/usr/bin/env python3
"""Conan test_package for perl-list-compare — Perl L1 test.

Tests that the installed List::Compare module can be loaded and used.
"""
import glob
import os

from conan import ConanFile


class PerlListCompareTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the Perl lib path from the installed package
        dep = self.dependencies["perl-list-compare"]
        site_perl_dirs = glob.glob(
            os.path.join(dep.package_folder, "usr", "local", "lib", "site_perl", "*")
        )
        if site_perl_dirs:
            perl_lib = site_perl_dirs[0]
        else:
            perl_lib = os.path.join(
                dep.package_folder, "usr", "local", "lib", "site_perl", "5.42.0"
            )
        os.environ["PERL5LIB"] = perl_lib

        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use List::Compare; '
            'my $lc = List::Compare->new([1,2,3], [2,3,4]); '
            'my @intersection = $lc->get_intersection; '
            'my @union = $lc->get_union; '
            'my @unique = $lc->get_unique; '
            'my @complement = $lc->get_complement; '
            'die "intersection failed" unless "@intersection" eq "2 3"; '
            'die "union failed" unless "@union" eq "1 2 3 4"; '
            'die "unique failed" unless "@unique" eq "1"; '
            'die "complement failed" unless "@complement" eq "4"; '
            'print "List::Compare test OK\n";'
        )
        self.run(f'perl -e \'{test_script}\'')
