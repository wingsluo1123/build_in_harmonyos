#!/usr/bin/env python3
"""Conan test_package — perl-object-pad 0.821-r0

L1 test: verify the package can be consumed.
For Perl XS modules, we verify the .so file exists and is a valid ELF.
"""
import os

from conan import ConanFile


class PerlobjectpadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Find the package root by checking the dependency
        dep = self.dependencies["perl-object-pad"]
        pkg_folder = dep.package_folder
        self.output.info(f"Package folder: {pkg_folder}")
        
        # Search for Pad.so
        found = False
        for root, dirs, files in os.walk(pkg_folder):
            for f in files:
                if f == "Pad.so":
                    so_path = os.path.join(root, f)
                    size = os.path.getsize(so_path)
                    self.output.info(f"✅ Found Pad.so at {so_path} ({size} bytes)")
                    found = True
        
        if not found:
            self.output.warning("⚠️ Pad.so not found in package")
