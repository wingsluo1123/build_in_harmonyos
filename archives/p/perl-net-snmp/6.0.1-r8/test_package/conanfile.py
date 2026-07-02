#!/usr/bin/env python3
"""Conan test_package — Perl module L1 test for perl-net-snmp.

Tests that Net::SNMP can be loaded via PERL5LIB and reports its version.
"""
import os

from conan import ConanFile


class PerlnetsnmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency
        pkg_folder = self.dependencies["perl-net-snmp"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib")
        # Verify the Perl module can be loaded
        self.run(f"PERL5LIB={perl_lib} perl -e 'use Net::SNMP; "
                 f"print \"Net::SNMP version: \", Net::SNMP->VERSION, \"\\n\";'")
