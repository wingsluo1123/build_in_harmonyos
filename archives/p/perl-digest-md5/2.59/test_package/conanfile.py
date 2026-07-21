#!/usr/bin/env python3
"""Conan test_package — Digest::MD5 Perl XS module.

Verifies that the package contains a valid .so artifact:
- Shared library (valid ELF magic)
- boot symbol (boot_Digest__MD5) present via nm -D
"""
import os
import subprocess

from conan import ConanFile


class TestPackageConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-digest-md5"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Walk package folder to find .so files
        so_files = []
        for root, dirs, files in os.walk(pkg_folder):
            for f in files:
                if f.endswith(".so"):
                    so_files.append(os.path.join(root, f))

        assert so_files, f"No .so files found in package {pkg_folder}"
        so_path = so_files[0]
        self.output.info(f"Found .so: {so_path}")

        # Verify ELF magic number
        with open(so_path, "rb") as fh:
            magic = fh.read(4)
            assert magic == b"\x7fELF", f"Not ELF format: magic={magic} for {so_path}"

        # Verify boot symbol exists via nm -D
        result = subprocess.run(
            ["nm", "-D", so_path],
            capture_output=True, text=True
        )
        assert "boot_Digest__MD5" in result.stdout, (
            f"Boot symbol 'boot_Digest__MD5' not found in {so_path}\n"
            f"nm -D output:\n{result.stdout}"
        )

        self.output.info(f"OK: MD5.so verified (ELF + boot_Digest__MD5)")
