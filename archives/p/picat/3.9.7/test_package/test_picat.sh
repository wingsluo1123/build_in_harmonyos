#!/usr/bin/env bash
# test_picat.sh — Smoke test for picat 3.9.7
# Verifies that the picat binary is functional after installation.
set -euo pipefail

# Find picat binary from the first argument (bin dir)
PICAT_BIN_DIR="$1"
PICAT="$PICAT_BIN_DIR/picat"
LIB_DIR="$(dirname "$PICAT_BIN_DIR")/share/picat/lib"
export PICATPATH="$LIB_DIR"

# Test 1: picat --version should output version string
output="$("$PICAT" --version 2>&1)"
echo "Test 1 (picat --version): $output"
echo "$output" | grep -q "Picat version 3.9#7" || {
    echo "FAIL: Expected 'Picat version 3.9#7' in output"
    exit 1
}

# Test 2: run a simple arithmetic program
test_pi="$(dirname "$0")/test_basic.pi"
output="$("$PICAT" "$test_pi" 2>&1)"
echo "Test 2 (arithmetic): $output"
echo "$output" | grep -q "^3$" || {
    echo "FAIL: Expected 3 as first output line"
    exit 1
}
echo "$output" | grep -q "^20$" || {
    echo "FAIL: Expected 20 as second output line"
    exit 1
}

echo "All tests passed."
