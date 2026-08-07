#!/usr/bin/env python3
"""Test script for List::MoreUtils::XS package verification.

Verifies that the package contains valid ELF .so and correct .pm file.

Usage: python3 test_package.py <so_path> <pm_path>

R34: Verifies actual build artifacts — XS.so must be valid ELF,
XS.pm must contain version string 0.430.
"""
import sys
import os


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_package.py <so_path> <pm_path>", file=sys.stderr)
        sys.exit(1)

    so_path = sys.argv[1]
    pm_path = sys.argv[2]

    errors = []

    # Check XS.so exists and is valid ELF
    if not os.path.exists(so_path):
        errors.append(f"XS.so not found at {so_path}")
    else:
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"XS.so is not valid ELF (magic: {magic})")
        # Check file size is reasonable (should be > 50KB)
        size = os.path.getsize(so_path)
        if size < 50000:
            errors.append(f"XS.so is suspiciously small: {size} bytes")

    # Check XS.pm exists and has correct version
    if not os.path.exists(pm_path):
        errors.append(f"XS.pm not found at {pm_path}")
    else:
        with open(pm_path, "r") as f:
            content = f.read()
            if "0.430" not in content:
                errors.append("XS.pm does not contain version 0.430")
            if "List::MoreUtils::XS" not in content:
                errors.append("XS.pm does not contain package name List::MoreUtils::XS")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print("OK: List::MoreUtils::XS package verified - XS.so (ELF valid), XS.pm (version 0.430)")
    sys.exit(0)


if __name__ == "__main__":
    main()
