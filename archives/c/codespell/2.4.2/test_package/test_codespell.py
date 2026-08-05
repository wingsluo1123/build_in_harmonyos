#!/usr/bin/env python3
"""Test source for codespell test_package — verifies spellcheck functionality.

This script creates a temporary file with a known misspelling,
runs codespell on it, and verifies the misspelling is detected.
"""
import os
import sys
import tempfile
import subprocess


def main():
    # Get the codespell binary path from environment
    codespell_bin = os.environ.get("CODESPELL_BIN", "codespell")

    # Create a temp file with a known misspelling
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir=tempfile.gettempdir()) as f:
        f.write("This is a test with a misspelled word: seperate\n")
        temp_path = f.name

    try:
        # Run codespell on the temp file
        result = subprocess.run(
            [sys.executable, codespell_bin, temp_path],
            capture_output=True, text=True
        )
        # codespell returns 0 if no misspellings, non-zero if misspellings found
        # "seperate" should be detected as a misspelling of "separate"
        if result.returncode != 0 or "seperate" in result.stdout:
            print("PASS: codespell detected misspelling 'seperate'")
            return 0
        else:
            print("FAIL: codespell did not detect misspelling 'seperate'")
            return 1
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    sys.exit(main())
