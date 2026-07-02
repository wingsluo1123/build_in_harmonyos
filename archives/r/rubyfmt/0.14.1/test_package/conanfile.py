#!/usr/bin/env python3
"""Conan test_package — rubyfmt 0.14.1

Tests the rubyfmt binary by:
1. Running --version
2. Formatting a simple Ruby snippet and checking output
"""
import os
import subprocess

from conan import ConanFile


class RubyfmtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Find the rubyfmt binary in the package folder
        rubyfmt_dep = self.dependencies["rubyfmt"]
        pkg_folder = rubyfmt_dep.package_folder
        bin_path = os.path.join(pkg_folder, "bin", "rubyfmt")

        if not os.path.exists(bin_path):
            # Fallback: search in package folder
            for root, dirs, files in os.walk(pkg_folder):
                if "rubyfmt" in files:
                    bin_path = os.path.join(root, "rubyfmt")
                    break

        assert os.path.exists(bin_path), f"rubyfmt binary not found at {bin_path}"
        self.output.info(f"Found rubyfmt at: {bin_path}")

        # Test 1: --version
        self.output.info("Testing rubyfmt --version...")
        self.run(f'"{bin_path}" --version', env="conanrun")

        # Test 2: Format Ruby code via stdin
        self.output.info("Testing rubyfmt formatting...")
        result = subprocess.run(
            [bin_path],
            input="def foo; 42; end\n",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"rubyfmt format failed: {result.stderr}"
        formatted = result.stdout.strip()
        expected = "def foo\n  42\nend"
        assert formatted == expected, f"Formatting mismatch:\nExpected:\n{expected}\nGot:\n{formatted}"
        self.output.info(f"Format test passed: {formatted}")
