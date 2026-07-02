#!/usr/bin/env python3
"""Conan test_package — Perl module Number::Compare.

Verifies the installed Perl module can be loaded and used.
"""
import os
import glob

from conan import ConanFile


class PerlNumberCompareTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Find the installed Perl module in the package folder
        dep = self.dependencies["perl-number-compare"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Compare.pm"), recursive=True)
        if not pm_files:
            try:
                resdirs = dep.cpp_info.resdirs
                if resdirs:
                    pm_files = glob.glob(os.path.join(resdirs[0], "**", "Compare.pm"), recursive=True)
            except Exception:
                pass
        if not pm_files:
            raise Exception("Number::Compare.pm not found in package")
        perl_lib = os.path.dirname(os.path.dirname(pm_files[0]))

        # Write test script to a file to avoid shell quoting issues
        test_script = os.path.join(self.build_folder, "test_compare.pl")
        with open(test_script, "w") as f:
            f.write(
                f"use lib '{perl_lib}';\n"
                "use Number::Compare;\n"
                "my $comp = Number::Compare->new('>10');\n"
                "die 'test failed' unless $comp->test(15);\n"
                "die 'test failed' if $comp->test(5);\n"
                "print 'Number::Compare test: OK\n';\n"
            )

    def test(self):
        test_script = os.path.join(self.build_folder, "test_compare.pl")
        self.run(f"perl {test_script}", env="conanrun")
