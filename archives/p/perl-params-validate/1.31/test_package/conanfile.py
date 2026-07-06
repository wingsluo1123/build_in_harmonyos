#!/usr/bin/env python3
"""Conan test_package for perl-params-validate — Perl L1 test.

Tests that the installed Params::Validate module can be loaded and used.
Note: XS .so may fail to load due to SELinux/HMDFS restrictions,
but Module::Implementation automatically falls back to PP mode.
"""
import os

from conan import ConanFile


class TestPerlParamsValidate(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package's install location
        dep = self.dependencies["perl-params-validate"]
        pkg_folder = dep.package_folder

        # Module installed to system Perl site_perl arch path
        site_arch = os.path.join(pkg_folder,
                                 "data", "service", "hnp", "perl.org",
                                 "perl_5.42.0", "lib", "site_perl", "5.42.0",
                                 "aarch64-linux")

        # Set PERL5LIB so Perl can find the installed module
        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = site_arch

        # Run the test script (test.sh wraps test.pl for CI L0c compliance)
        test_script = os.path.join(self.source_folder, "test.sh")
        try:
            self.run(f"sh {test_script}")
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
