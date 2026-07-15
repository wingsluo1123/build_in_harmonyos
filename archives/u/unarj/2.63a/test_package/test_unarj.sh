#!/bin/bash
# test_unarj.sh — Smoke test for unarj binary
# Usage: bash test_unarj.sh /path/to/unarj
set -euo pipefail

UNARJ_BIN="$1"
if [ -z "$UNARJ_BIN" ]; then
    echo "ERROR: unarj binary path not provided"
    exit 1
fi

if [ ! -f "$UNARJ_BIN" ]; then
    echo "ERROR: unarj binary not found at $UNARJ_BIN"
    exit 1
fi

# Test 1: Run unarj with no args — should print usage info
# unarj exits non-zero when run with no args (prints usage), so suppress exit code
output=$("$UNARJ_BIN" 2>&1) || true
echo "$output" | grep -i "unarj" > /dev/null && echo "PASS: unarj prints usage info" || {
    echo "FAIL: unarj did not print expected output"
    exit 1
}

echo "All tests passed."
