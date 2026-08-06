#!/bin/bash
# test.sh — gleam test_package
# Tests that the gleam binary works correctly by running --version
set -e

# Find the gleam binary from the conan package
GLEAM_BIN=$(find "$(dirname "$0")/.." -name "gleam" -path "*/bin/*" -type f 2>/dev/null | head -1)

# Fallback: search in common conan package paths
if [ -z "$GLEAM_BIN" ]; then
    # Try using the PATH from conanrun environment
    GLEAM_BIN=$(which gleam 2>/dev/null)
fi

if [ -z "$GLEAM_BIN" ]; then
    echo "ERROR: gleam binary not found"
    exit 1
fi

echo "Found gleam at: $GLEAM_BIN"

# Test 1: Verify gleam binary executes and reports version
# R34: test must actually exercise the tested package's binary
output=$("$GLEAM_BIN" --version 2>&1)
exit_code=$?
echo "Output: $output"
echo "Exit code: $exit_code"

if [ $exit_code -ne 0 ]; then
    echo "FAIL: gleam --version exited with $exit_code"
    exit 1
fi

if echo "$output" | grep -q "gleam 1.17.0"; then
    echo "PASS: gleam --version reports correct version"
else
    echo "FAIL: gleam --version output does not contain expected version"
    exit 1
fi

echo "All tests passed."
