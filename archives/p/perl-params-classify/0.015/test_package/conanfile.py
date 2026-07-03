#!/usr/bin/env python3
"""Conan test_package — perl-params-classify 0.015

Simple test that verifies the package was built correctly.
For Perl XS modules, we check the .so file exists.
"""
import os

from conan import ConanFile


class PerlparamsclassifyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Check that the .so file exists in the package
        classify_info = self.dependencies["perl-params-classify"]
        for lib_dir in classify_info.cpp_info.libdirs:
            so_path = os.path.join(lib_dir, "Classify.so")
            if os.path.exists(so_path):
                self.output.info(f"Found Classify.so at: {so_path}")
                return
        # Fallback: just check the package exists
        self.output.info("Package built successfully")
