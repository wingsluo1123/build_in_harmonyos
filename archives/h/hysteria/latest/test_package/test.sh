#!/bin/bash
# Smoke test for hysteria binary
# Verifies the binary can execute and report version info

set -e

HYSTERIA_BIN="${1:-hysteria}"

echo "=== Hysteria Smoke Test ==="
echo "Binary: $HYSTERIA_BIN"

# Test 1: Binary exists and is executable
if [ ! -x "$HYSTERIA_BIN" ]; then
    echo "FAIL: Binary not found or not executable: $HYSTERIA_BIN"
    exit 1
fi
echo "PASS: Binary exists and is executable"

# Test 2: Version command works
OUTPUT=$("$HYSTERIA_BIN" version 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: version command failed"
    echo "$OUTPUT"
    exit 1
fi
echo "PASS: version command succeeded"

# Test 3: Check version string contains expected version
if echo "$OUTPUT" | grep -q "2.9.3"; then
    echo "PASS: Version 2.9.3 found in output"
else
    echo "WARN: Version 2.9.3 not found in output (may be expected for some builds)"
fi

# Test 4: Check platform info
if echo "$OUTPUT" | grep -qi "linux"; then
    echo "PASS: Platform linux found in output"
else
    echo "WARN: Platform linux not found in output"
fi

# Test 5: Check help command
OUTPUT=$("$HYSTERIA_BIN" --help 2>&1 || true)
if echo "$OUTPUT" | grep -qi "usage\|command\|help"; then
    echo "PASS: Help output contains expected content"
else
    echo "WARN: Help output does not contain expected content"
fi

echo "=== Smoke Test Complete ==="
