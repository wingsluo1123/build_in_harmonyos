#!/bin/sh
# test_package/test_mc.sh — Test mc binary functionality
# Verifies that the mc binary is installed and can report its version.
# This test exercises the actual mc package binary.

set -e

MC_BIN="${MC_BIN:-mc}"

# Test 1: mc --version should output version info
output=$("$MC_BIN" --version 2>&1) || {
    echo "FAIL: mc --version exited with error"
    exit 1
}

# Verify output contains "Midnight Commander"
echo "$output" | grep -q "Midnight Commander" || {
    echo "FAIL: mc --version output doesn't contain 'Midnight Commander'"
    echo "Got: $output"
    exit 1
}

echo "PASS: mc --version works correctly"
echo "Output: $output" | head -3
