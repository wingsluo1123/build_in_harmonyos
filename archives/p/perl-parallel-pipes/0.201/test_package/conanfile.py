#!/usr/bin/env python3
"""Conan test_package — Parallel::Pipes (pure Perl module)."""
import os
import glob

from conan import ConanFile


class PerlparallelpipesTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-parallel-pipes"]
        pkg_folder = dep.package_folder
        pipes_files = glob.glob(os.path.join(pkg_folder, "**", "Parallel", "Pipes.pm"), recursive=True)
        if not pipes_files:
            raise Exception("Parallel/Pipes.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pipes_files[0]))

        # Set PERL5LIB and run test.sh (CI L0c compliant)
        os.environ["PERL5LIB"] = perl_lib_dir
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_script}")
