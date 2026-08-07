#!/usr/bin/env python3
"""Conan test_package — Module::Runtime (pure Perl module).

Verifies that Module::Runtime is correctly installed and functional by
loading the module and calling its core API functions.
"""
import os
import glob
import tempfile

from conan import ConanFile


class PerlModuleRuntimeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-module-runtime"]
        pkg_folder = dep.package_folder
        runtime_files = glob.glob(
            os.path.join(pkg_folder, "**", "Module", "Runtime.pm"),
            recursive=True,
        )
        if not runtime_files:
            raise Exception("Module/Runtime.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(runtime_files[0]))

        # Write a test script that exercises Module::Runtime API
        test_script = os.path.join(tempfile.gettempdir(), "test_module_runtime.pl")
        with open(test_script, "w") as f:
            f.write("use Module::Runtime qw(require_module use_module is_module_name);\n")
            f.write("die 'not a valid module name' unless is_module_name('Cwd');\n")
            f.write("require_module('Cwd');\n")
            f.write("use_module('Cwd');\n")
            f.write("print Cwd::getcwd(), \"\\n\";\n")
            f.write("print \"OK\\n\";\n")
        self.run(
            'PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script)
        )
