#!/usr/bin/env python3
"""Conan test_package — Perl module Number::Compare.

Verifies the installed Perl module can be loaded and used.
"""
from conan import ConanFile


class PerlNumberCompareTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PERL5LIB is set by conanrun env (from package_info runenv_info)
        self.run("sh test_compare.sh", env="conanrun")
