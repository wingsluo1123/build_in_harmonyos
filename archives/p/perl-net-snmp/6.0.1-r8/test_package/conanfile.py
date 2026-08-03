#!/usr/bin/env python3
"""Conan test_package — Perl module test (L1).

Verifies that Net::SNMP is properly packaged and loadable.
"""
import os
import shutil

from conan import ConanFile


class PerlnetsnmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency (Conan 2.x API)
        pkg_folder = self.dependencies["perl-net-snmp"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib")
        self.output.info("Using PERL5LIB={}".format(perl_lib))

        # Copy external test script to build folder and run it
        test_script = os.path.join(self.build_folder, "test_snmp.pl")
        shutil.copy(os.path.join(self.source_folder, "test_snmp.pl"), test_script)
        self.run('PERL5LIB="{}" perl "{}"'.format(perl_lib, test_script), env="conanrun")
