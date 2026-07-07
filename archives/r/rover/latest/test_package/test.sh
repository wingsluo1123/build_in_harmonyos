#!/bin/sh
# Smoke test for rover binary
# Usage: test.sh /path/to/rover

set -e

ROVER_BIN="${1:-rover}"

echo "=== Rover Smoke Test ==="

# Test 1: Version check
echo -n "Test 1 - Version check: "
VERSION_OUTPUT=$("$ROVER_BIN" --version 2>&1)
if echo "$VERSION_OUTPUT" | grep -q "Rover"; then
    echo "PASS ($VERSION_OUTPUT)"
else
    echo "FAIL (expected 'Rover ...', got: $VERSION_OUTPUT)"
    exit 1
fi

# Test 2: Help command
echo -n "Test 2 - Help command: "
HELP_OUTPUT=$("$ROVER_BIN" --help 2>&1)
if echo "$HELP_OUTPUT" | grep -q "Usage"; then
    echo "PASS"
else
    echo "FAIL (expected 'Usage' in help output)"
    exit 1
fi

# Test 3: Subcommand listing (use grep -E for OHOS toybox compat)
echo -n "Test 3 - Subcommand listing: "
SUBCMD_OUTPUT=$("$ROVER_BIN" --help 2>&1)
if echo "$SUBCMD_OUTPUT" | grep -qE "init|graph|subgraph|introspect"; then
    echo "PASS"
else
    echo "FAIL (expected subcommands in help)"
    exit 1
fi

echo "=== All smoke tests passed ==="
