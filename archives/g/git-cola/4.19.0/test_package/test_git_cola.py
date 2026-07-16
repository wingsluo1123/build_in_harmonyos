#!/usr/bin/env python3
"""Test script for git-cola package.
Verifies that the cola Python module can be imported and reports correct version.
"""
import sys
import importlib

def main():
    # Test: import cola._version and check version
    try:
        version_module = importlib.import_module("cola._version")
        version = getattr(version_module, "VERSION", None)
        if version != "4.19.0":
            print(f"FAIL: Expected version 4.19.0, got {version}")
            sys.exit(1)
        print(f"OK: git-cola version {version}")
    except ImportError as e:
        print(f"FAIL: Cannot import cola._version: {e}")
        sys.exit(1)

    # Test: import cola.main
    try:
        importlib.import_module("cola.main")
        print("OK: cola.main imported successfully")
    except ImportError as e:
        print(f"FAIL: Cannot import cola.main: {e}")
        sys.exit(1)

    print("All tests passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
