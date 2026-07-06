#!/usr/bin/env python3
"""Conan test_package — perl-par-packer 1.064-r2.

Tests that the PAR::Packer Perl module files are correctly packaged.
Note: Cannot use `perl -e 'use PAR'` because PAR tries to create a cache
directory which fails on OHOS due to HMDFS restrictions (platform limitation).
"""
import os

from conan import ConanFile


class PerlParPackerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build needed for Perl module test

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["perl-par-packer"]
        perl_lib = os.path.join(dep.package_folder, "lib", "perl5")

        # Verify key module files exist
        required_files = [
            "PAR/Packer.pm",
            "PAR/StrippedPARL/Base.pm",
            "pp.pm",
        ]

        for rel_path in required_files:
            full_path = os.path.join(perl_lib, rel_path)
            assert os.path.exists(full_path), f"Required file not found: {rel_path} (expected at {full_path})"
            self.output.info(f"✅ Found: {rel_path}")

        # Check for XS .so files (optional - XSFoo.so is a test module)
        so_found = False
        for root, dirs, files in os.walk(perl_lib):
            for f in files:
                if f.endswith(".so"):
                    self.output.info(f"✅ XS module: {os.path.relpath(os.path.join(root, f), perl_lib)}")
                    so_found = True

        if so_found:
            self.output.info("XS .so modules found in package")
        else:
            self.output.info("No .so XS modules in package (expected - XSFoo is a test module)")

        # Verify scripts exist
        bin_dir = os.path.join(dep.package_folder, "bin")
        if os.path.exists(bin_dir):
            for f in os.listdir(bin_dir):
                self.output.info(f"✅ Script: {f}")

        self.output.info("All package content verified successfully")
