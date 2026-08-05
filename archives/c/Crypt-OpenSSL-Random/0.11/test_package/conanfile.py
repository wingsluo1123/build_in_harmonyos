#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Random Perl XS module.

Verifies that the package contains the expected artifacts:
- Random.so (shared library, valid ELF)
- Random.pm (Perl module file with version 0.11)
"""
import os

from conan import ConanFile


class CryptopensslrandomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get package folder from dependency
        dep = self.dependencies["crypt-openssl-random"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Paths to verify
        so_path = os.path.join(pkg_folder, "lib", "auto", "Crypt", "OpenSSL", "Random", "Random.so")
        pm_path = os.path.join(pkg_folder, "lib", "Crypt", "OpenSSL", "Random.pm")

        # Run the test script with paths as arguments
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run(f'python3 "{test_script}" "{so_path}" "{pm_path}"')
