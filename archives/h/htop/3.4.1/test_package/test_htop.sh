#!/bin/sh
# test_htop.sh — smoke test for htop package
# Verifies htop binary is installed, executable, and reports correct version

set -e

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    # Try to find htop in PATH
    HTOP_BIN="htop"
else
    HTOP_BIN="$BIN_DIR/htop"
fi

# Check binary exists
if ! command -v "$HTOP_BIN" >/dev/null 2>&1 && [ ! -x "$HTOP_BIN" ]; then
    echo "FAIL: htop binary not found"
    exit 1
fi

# Check --version output
OUTPUT=$("$HTOP_BIN" --version 2>&1)
echo "htop --version output: $OUTPUT"

# Verify version string
if echo "$OUTPUT" | grep -q "3.4.1"; then
    echo "PASS: htop version 3.4.1 confirmed"
    exit 0
else
    echo "FAIL: htop version mismatch"
    exit 1
fi
