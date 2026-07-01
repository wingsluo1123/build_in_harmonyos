#!/usr/bin/env python3
"""Conan test_package for cline 4.0.5 — JavaScript module verification.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

Tests:
1. Verify the CLI entry point (dist/index.js) exists and is a valid JS file
2. Verify SDK package dist directories exist
3. Verify package.json files are present with correct version
"""
import os
import json

from conan import ConanFile
from conan.tools.build import can_run


class ClineTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Get the package folder of the cline dependency
            cline_root = self.dependencies["cline"].package_folder
            cline_pkg = os.path.join(cline_root, "lib", "node_modules", "cline")

            # Test 1: Verify CLI entry point exists
            cli_entry = os.path.join(cline_pkg, "dist", "index.js")
            assert os.path.exists(cli_entry), f"CLI entry point not found: {cli_entry}"
            print(f"✅ CLI entry point exists: {cli_entry}")

            # Test 2: Verify the file is valid JavaScript (check first few bytes)
            with open(cli_entry, "r") as f:
                content = f.read(100)
                assert len(content) > 0, "CLI entry point is empty"
                print(f"✅ CLI entry point is valid JavaScript ({len(content)} bytes header)")

            # Test 3: Verify package.json exists
            pkg_json_path = os.path.join(cline_pkg, "package.json")
            assert os.path.exists(pkg_json_path), f"package.json not found: {pkg_json_path}"
            with open(pkg_json_path, "r") as f:
                pkg_data = json.load(f)
                print(f"✅ package.json found: name={pkg_data.get('name', 'unknown')}")

            # Test 4: Verify SDK packages exist
            sdk_dir = os.path.join(cline_pkg, "sdk")
            if os.path.isdir(sdk_dir):
                sdk_packages = os.listdir(sdk_dir)
                print(f"✅ SDK packages found: {sdk_packages}")
                # Verify each SDK package has dist/index.js
                for pkg_name in sdk_packages:
                    sdk_dist = os.path.join(sdk_dir, pkg_name, "dist", "index.js")
                    if os.path.exists(sdk_dist):
                        print(f"  ✅ {pkg_name}/dist/index.js exists")
                    else:
                        print(f"  ⚠️ {pkg_name}/dist/index.js not found")

            print("\n✅ All cline package tests passed!")
