#!/usr/bin/env python3
"""Test package for perl-object-insideout — verifies the Perl module loads."""
import os

from conan import ConanFile
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Copy the Perl module files to a local lib directory
        perl_lib = os.path.join(self.build_folder, "perl_lib")
        dep_pkg = self.dependencies["perl-object-insideout"].package_folder
        copy(self, "*.pm", os.path.join(dep_pkg, "lib"), perl_lib)
        copy(self, "*.pod", os.path.join(dep_pkg, "lib"), perl_lib)
        # Object::InsideOut must be used inside a class package, not from main.
        # Write a test script that properly uses the module.
        test_pl = os.path.join(self.build_folder, "test_oio.pl")
        with open(test_pl, "w") as f:
            f.write(
                "package My::Test;\n"
                "use Object::InsideOut;\n"
                "1;\n"
                "package main;\n"
                "print('Object::InsideOut version: ' . $Object::InsideOut::VERSION . \"\\n\");\n"
                "print(\"Test OK\\n\");\n"
            )
        self.run(f"perl -I{perl_lib} {test_pl}")
