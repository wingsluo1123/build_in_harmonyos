#!/usr/bin/env python3
"""Test script for glances 4.5.4 — package smoke test (R34).

Verifies that the glances package is correctly installed and accessible.
This script is called by test_package/conanfile.py test() method.
"""
import os
import sys


def test_package_exists():
    """Verify glances Python package directory exists."""
    pkg_root = os.environ.get("CONAN_GLANCES_ROOT", "")
    if not pkg_root:
        print("SKIP: CONAN_GLANCES_ROOT not set")
        return True

    glances_dir = os.path.join(pkg_root, "glances")
    if os.path.isdir(glances_dir):
        print(f"PASS: glances package found at {glances_dir}")
        return True
    else:
        print(f"FAIL: glances package not found at {glances_dir}")
        return False


def test_version():
    """Verify glances __version__ is 4.5.4."""
    pkg_root = os.environ.get("CONAN_GLANCES_ROOT", "")
    init_file = os.path.join(pkg_root, "glances", "__init__.py")
    if not os.path.isfile(init_file):
        print(f"FAIL: __init__.py not found at {init_file}")
        return False

    with open(init_file, "r") as f:
        content = f.read()
        if '__version__ = "4.5.4"' in content:
            print("PASS: glances version 4.5.4 confirmed")
            return True
        else:
            print("FAIL: version not 4.5.4")
            return False


def test_binary_exists():
    """Verify glances binary/script exists."""
    pkg_root = os.environ.get("CONAN_GLANCES_ROOT", "")
    glances_bin = os.path.join(pkg_root, "bin", "glances")
    if os.path.isfile(glances_bin):
        print(f"PASS: glances binary found at {glances_bin}")
        return True
    else:
        print(f"FAIL: glances binary not found at {glances_bin}")
        return False


if __name__ == "__main__":
    results = [test_package_exists(), test_version(), test_binary_exists()]
    if all(results):
        print("\nAll glances tests passed.")
        sys.exit(0)
    else:
        failed = sum(1 for r in results if not r)
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
