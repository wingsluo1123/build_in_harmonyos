#!/usr/bin/env python3
"""Conan test_package — Module::Runtime (pure Perl module).

Verifies that Module::Runtime is correctly installed and functional by
loading the module and calling its core API functions.
"""
import os
import glob
import shutil
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

        # Copy the test script to a temp location and run it
        test_script_src = os.path.join(os.path.dirname(__file__), "test_module_runtime.sh")
        tmp_script = os.path.join(tempfile.gettempdir(), "test_module_runtime_ohs.sh")
        if os.path.abspath(test_script_src) != os.path.abspath(tmp_script):
            shutil.copy2(test_script_src, tmp_script)

        self.run(
            'PERL5LIB="{}" bash {}'.format(perl_lib_dir, tmp_script)
        )
