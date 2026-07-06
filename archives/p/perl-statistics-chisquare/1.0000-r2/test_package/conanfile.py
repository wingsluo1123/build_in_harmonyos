#!/usr/bin/env python3
"""Conan test_package — Statistics::ChiSquare (pure Perl module)."""
import os
import glob

from conan import ConanFile


class PerlstatisticschisquareTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-statistics-chisquare"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Statistics", "ChiSquare.pm"), recursive=True)
        if not pm_files:
            raise Exception("Statistics/ChiSquare.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        # Write test script to the build folder (not /tmp — E002: /tmp is read-only on OHOS)
        test_script = os.path.join(self.build_folder, "test_statistics_chisquare.pl")
        with open(test_script, "w") as f:
            f.write("use Statistics::ChiSquare;\n")
            f.write("my @data = (500, 500);\n")
            f.write("my $result = chisquare(@data);\n")
            f.write("print $result . \"\\n\";\n")
            f.write("print \"OK\\n\" if $result;\n")
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script))
