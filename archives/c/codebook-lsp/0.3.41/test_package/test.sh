#!/bin/sh
# test_package/test.sh — Smoke test for codebook-lsp binary
#
# This script verifies the installed codebook-lsp binary is executable
# and reports the correct version string.
#
# Usage: Called by Conan test_package conanfile.py test() method
#   self.run("./test.sh", env="conanrun")

set -e

# Run codebook-lsp --version and verify output
VERSION_OUTPUT=$(codebook-lsp --version 2>&1)
EXPECTED_VERSION="codebook-lsp 0.3.41"

if [ "$VERSION_OUTPUT" = "$EXPECTED_VERSION" ]; then
    echo "PASS: codebook-lsp --version output matches expected ($EXPECTED_VERSION)"
    exit 0
else
    echo "FAIL: expected '$EXPECTED_VERSION', got '$VERSION_OUTPUT'"
    exit 1
fi
