#!/usr/bin/env python3
"""Conan test_package for perl-params-validationcompiler — Perl L1 test.

Tests that the installed Params::ValidationCompiler module can be loaded and used.
"""
from conan import ConanFile


class PerlparamsvalidationcompilerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and basic functionality works
        test_script = (
            'use Params::ValidationCompiler qw(validation_for); '
            'use Params::ValidationCompiler::Exceptions; '
            'my $validator = validation_for( params => { foo => 1 } ); '
            'die "test failed" unless $validator; '
            'print "Params::ValidationCompiler test OK\\n";'
        )
        self.run(f'perl -e \'{test_script}\'')
