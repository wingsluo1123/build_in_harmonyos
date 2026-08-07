#!/usr/bin/env python3
"""Conan test_package — IPC::ShareLite Perl XS module.

Verifies that the package contains the expected artifacts:
- ShareLite.so (shared library, valid ELF)
- ShareLite.pm (Perl module file with version 0.17)
"""
import os

from conan import ConanFile


class PerlipcshareliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get package folder from dependency
        dep = self.dependencies["perl-ipc-sharelite"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Paths to verify
        so_path = os.path.join(pkg_folder, "lib", "auto", "IPC", "ShareLite", "ShareLite.so")
        pm_path = os.path.join(pkg_folder, "lib", "IPC", "ShareLite.pm")

        # Run the test script with paths as arguments
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{so_path}" "{pm_path}"')
