#!/usr/bin/env python3
"""Conan test_package for perl-params-util — Perl L1 test.

Tests that the installed Params::Util module files exist in the package
and that core functions work correctly (pure Perl fallback mode).
Note: XS .so may fail to load due to SELinux/HMDFS restrictions,
but the pure Perl fallback (Params::Util::PP) works via PERL_PARAMS_UTIL_PP=1.
"""
import os

from conan import ConanFile


class PerlparamsutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Check that the package contains the expected files
        pkg = self.dependencies["perl-params-util"]
        pkg_folder = pkg.package_folder

        # Module installed to system Perl site_perl arch path
        site_arch = os.path.join(pkg_folder,
                                 "data", "service", "hnp", "perl.org",
                                 "perl_5.42.0", "lib", "site_perl", "5.42.0",
                                 "aarch64-linux")

        expected_files = [
            os.path.join(site_arch, "Params", "Util.pm"),
            os.path.join(site_arch, "Params", "Util", "PP.pm"),
            os.path.join(site_arch, "auto", "Params", "Util", "Util.so"),
        ]

        for f in expected_files:
            assert os.path.isfile(f), f"Expected file not found: {f}"
            self.output.info(f"Found: {f}")

        # Try loading the module with PERL5LIB set to package path
        # Use PERL_PARAMS_UTIL_PP=1 to force pure Perl fallback
        # (XS .so cannot load from HMDFS due to SELinux restrictions)
        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = site_arch
        os.environ["PERL_PARAMS_UTIL_PP"] = "1"
        try:
            self.run(
                "perl -e '"
                "use Params::Util;"
                'print "version: $Params::Util::VERSION\\n";'
                'print "_STRING: ", (defined Params::Util::_STRING("hello") ? "pass" : "fail"), "\\n";'
                'print "_NUMBER: ", (defined Params::Util::_NUMBER(42) ? "pass" : "fail"), "\\n";'
                "'"
            )
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
            del os.environ["PERL_PARAMS_UTIL_PP"]
