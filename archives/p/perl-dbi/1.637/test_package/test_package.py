#!/usr/bin/env python3
"""Test script for DBI package verification.
Verifies that the package contains valid ELF .so and correct .pm file.

Usage: python3 test_package.py <pkg_folder>
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pkg_folder>", file=sys.stderr)
        sys.exit(1)

    pkg_folder = sys.argv[1]
    errors = []

    # Find .so file by walking the package folder
    so_path = None
    for root, dirs, files in os.walk(pkg_folder):
        for f in files:
            if f.endswith(".so"):
                so_path = os.path.join(root, f)
                break
        if so_path:
            break

    if not so_path:
        errors.append("No .so file found in package")
    else:
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"{f} is not valid ELF (magic: {magic})")

    # Find .pm file by walking the package folder
    pm_path = None
    for root, dirs, files in os.walk(pkg_folder):
        for f in files:
            if f.endswith(".pm"):
                pm_path = os.path.join(root, f)
                break
        if pm_path:
            break

    if not pm_path:
        errors.append("No .pm file found in package")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: DBI package verified - .so (ELF valid), .pm found")
    sys.exit(0)


if __name__ == "__main__":
    main()
