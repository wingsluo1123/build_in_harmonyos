#!/usr/bin/env python3
"""Test source file for Pod::Wrap test_package.

Verifies that the package contains the Wrap.pm file with correct version
and package name.

Usage: python3 test_package.py <pm_path>
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pm_path>", file=sys.stderr)
        sys.exit(1)

    pm_path = sys.argv[1]
    errors = []

    if not os.path.exists(pm_path):
        errors.append(f"Wrap.pm not found at {pm_path}")
    else:
        with open(pm_path, "r") as f:
            content = f.read()
            if "0.01" not in content:
                errors.append("Wrap.pm does not contain version 0.01")
            if "Pod::Wrap" not in content:
                errors.append("Wrap.pm does not contain package name Pod::Wrap")
            if "Pod::Parser" not in content:
                errors.append("Wrap.pm does not inherit from Pod::Parser")
            if "Text::Wrap" not in content:
                errors.append("Wrap.pm does not use Text::Wrap")
            if "textblock" not in content:
                errors.append("Wrap.pm does not define textblock method")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: Pod::Wrap package verified - Wrap.pm (version 0.01, inherits Pod::Parser, uses Text::Wrap)")
    sys.exit(0)


if __name__ == "__main__":
    main()
