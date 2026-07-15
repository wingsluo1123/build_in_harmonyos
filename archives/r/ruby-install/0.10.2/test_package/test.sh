#!/usr/bin/env bash
# test.sh — smoke test for ruby-install package
# Verifies that the ruby-install script is installed and functional.
set -euo pipefail

# Find the ruby-install binary from the package
RUBY_INSTALL="${1:-ruby-install}"

# Test 1: Check the script exists and is executable
if [ ! -x "$RUBY_INSTALL" ]; then
    echo "ERROR: ruby-install not found or not executable: $RUBY_INSTALL"
    exit 1
fi

# Test 2: Check --version output (verify the tool is functional)
# Note: upstream 0.10.2 release has a hardcoded version of 0.10.1 in the source
# Capture output even on non-zero exit (version/help may return 1)
VERSION=$("$RUBY_INSTALL" --version 2>&1 || true)
if echo "$VERSION" | grep -qi "ruby-install"; then
    echo "PASS: ruby-install --version works: $VERSION"
else
    echo "FAIL: ruby-install --version unexpected output: $VERSION"
    exit 1
fi

# Test 3: Check --help output (verify help system works)
# Capture output even on non-zero exit (help may return 1)
OUTPUT=$("$RUBY_INSTALL" --help 2>&1 || true)
if echo "$OUTPUT" | grep -qi "ruby-install"; then
    echo "PASS: ruby-install --help shows usage information"
else
    echo "FAIL: ruby-install --help does not show expected output"
    echo "$OUTPUT"
    exit 1
fi

echo "All smoke tests passed."
