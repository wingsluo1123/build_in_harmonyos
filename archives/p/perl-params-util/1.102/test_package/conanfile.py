#!/usr/bin/env python3
"""Conan test_package for perl-params-util — Perl L1 test.

Tests that the installed Params::Util module files exist in the package.
Note: XS .so may fail to load due to OHOS ELF signing restrictions,
but the pure Perl fallback should still work with PERL_PARAMS_UTIL_PP=1.
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

        # Try loading the module in pure Perl mode (PERL_PARAMS_UTIL_PP=1)
        # XS .so may fail to load due to OHOS ELF signing
        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = site_arch
        os.environ["PERL_PARAMS_UTIL_PP"] = "1"
        try:
            self.run(
                'perl -MParams::Util -e "'
                'print qq(version: $Params::Util::VERSION\\n);'
                'print qq(_STRING: ), (defined Params::Util::_STRING(q{hello}) ? q{pass} : q{fail}), qq(\\n);'
                '"'
            )
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
            del os.environ["PERL_PARAMS_UTIL_PP"]
