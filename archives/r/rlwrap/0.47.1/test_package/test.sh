#!/bin/sh
# test_package smoke test for rlwrap
# Verifies that the rlwrap binary is executable and reports its version.
# Usage: ./test.sh <path-to-rlwrap-binary>
set -e

RLWRAP_BIN="$1"
if [ -z "$RLWRAP_BIN" ]; then
    echo "ERROR: rlwrap binary path not provided"
    echo "Usage: $0 <path-to-rlwrap-binary>"
    exit 1
fi

if [ ! -f "$RLWRAP_BIN" ]; then
    echo "ERROR: rlwrap binary not found at $RLWRAP_BIN"
    exit 1
fi

# HMDFS bless: re-create binary to ensure execute permission
cp "$RLWRAP_BIN" "$RLWRAP_BIN.bless"
rm "$RLWRAP_BIN"
cp "$RLWRAP_BIN.bless" "$RLWRAP_BIN"
rm "$RLWRAP_BIN.bless"
chmod 755 "$RLWRAP_BIN"

# Run version check
output=$("$RLWRAP_BIN" --version 2>&1)
echo "$output"

# Verify output contains "rlwrap"
if echo "$output" | grep -q "rlwrap"; then
    echo "PASS: rlwrap --version output verified"
    exit 0
else
    echo "FAIL: rlwrap --version did not contain expected output"
    exit 1
fi
