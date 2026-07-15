#!/system/bin/sh
# test.sh — massdns smoke test
# Verifies that the massdns binary is installed and functional.
# Called by test_package/conanfile.py with MASSDNS_BIN env var set.

set -eu

MASSDNS_BIN="${MASSDNS_BIN:?MASSDNS_BIN not set}"

# Verify binary exists
if [ ! -f "$MASSDNS_BIN" ]; then
    echo "FAIL: massdns binary not found at $MASSDNS_BIN"
    exit 1
fi

# Run massdns --version and check output
OUTPUT=$("$MASSDNS_BIN" --version 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: massdns --version exited with error"
    exit 1
fi

# massdns --version outputs "massdns"
if echo "$OUTPUT" | grep -q "massdns"; then
    echo "PASS: massdns binary is functional"
    exit 0
else
    echo "FAIL: unexpected output from massdns --version: $OUTPUT"
    exit 1
fi
