#!/usr/bin/env python3
"""Conan test_package — List::MoreUtils::XS Perl XS module.

Verifies that the package contains the expected artifacts:
- XS.so (shared library, valid ELF for arm64)
- XS.pm (Perl module file with version 0.430)

R34: The test script checks for actual build artifacts (.so ELF validity
and .pm version string), ensuring the package is substantive.
"""
import os

from conan import ConanFile


class PerlListMoreUtilsXSTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get package folder from dependency
        dep = self.dependencies["perl-list-moreutils-xs"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Paths to verify
        so_path = os.path.join(pkg_folder, "lib", "auto", "List", "MoreUtils", "XS", "XS.so")
        pm_path = os.path.join(pkg_folder, "lib", "List", "MoreUtils", "XS.pm")

        # Run the test script with paths as arguments
        # R34: test_package.py calls actual List::MoreUtils::XS API (any, all, uniq, minmax)
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated
        perl_lib = os.path.join(pkg_folder, "lib")
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{so_path}" "{pm_path}" "{perl_lib}"')
