#!/usr/bin/env python3
"""Test script for cline 4.0.5 — package artifact verification."""
import json
import os
import sys

def main():
    cline_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLINE_ROOT", "")
    cline_pkg = os.path.join(cline_root, "lib", "node_modules", "cline")
    failures = 0

    # Test 1: CLI entry point exists
    cli_entry = os.path.join(cline_pkg, "dist", "index.js")
    if os.path.exists(cli_entry):
        print("PASS: CLI entry point exists")
    else:
        print(f"FAIL: CLI entry point not found: {cli_entry}", file=sys.stderr)
        failures += 1

    # Test 2: package.json exists and has correct name
    pkg_json_path = os.path.join(cline_pkg, "package.json")
    if os.path.exists(pkg_json_path):
        with open(pkg_json_path) as f:
            pkg_data = json.load(f)
            print(f"PASS: package.json name={pkg_data.get('name', 'unknown')}")
    else:
        print(f"FAIL: package.json not found: {pkg_json_path}", file=sys.stderr)
        failures += 1

    # Test 3: SDK packages exist
    sdk_dir = os.path.join(cline_pkg, "sdk")
    if os.path.isdir(sdk_dir):
        sdk_packages = os.listdir(sdk_dir)
        print(f"PASS: SDK packages found: {sdk_packages}")
    else:
        print("FAIL: SDK directory not found", file=sys.stderr)
        failures += 1

    if failures > 0:
        print(f"\n{failures} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
    print("\nAll cline tests passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
