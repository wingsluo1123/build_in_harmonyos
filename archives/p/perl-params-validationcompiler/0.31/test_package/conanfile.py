#!/usr/bin/env python3
"""Conan test_package for perl-params-validationcompiler — Perl L1 test.

Tests that the installed Params::ValidationCompiler module can be loaded and used.
"""
import os
import glob

from conan import ConanFile


class PerlparamsvalidationcompilerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-params-validationcompiler"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Params", "ValidationCompiler.pm"), recursive=True)
        if not pm_files:
            raise Exception("Params/ValidationCompiler.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Set PERL5LIB and run test.sh (CI L0c compliant)
        os.environ["PERL5LIB"] = perl_lib_dir
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_script}")
