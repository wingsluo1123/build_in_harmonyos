#!/usr/bin/env bash
set -euo pipefail

# c-blosc2 test_package verification script
# Usage: test.sh [path/to/test_package_binary]

TEST_BIN="${1:-test_package}"

# Verify the test binary exists
if [ ! -f "$TEST_BIN" ]; then
    echo "ERROR: $TEST_BIN does not exist" >&2
    exit 1
fi

# If the binary is executable, run it and verify output
if [ -x "$TEST_BIN" ]; then
    set +e
    output=$("$TEST_BIN" 2>&1)
    rc=$?
    set -e
    if [ $rc -ne 0 ]; then
        echo "ERROR: $TEST_BIN exited with code $rc" >&2
        echo "Output was:" >&2
        echo "$output" >&2
        exit 1
    fi
    if ! echo "$output" | grep -q "Successful roundtrip!"; then
        echo "ERROR: test_package did not output 'Successful roundtrip!'" >&2
        echo "Output was:" >&2
        echo "$output" >&2
        exit 1
    fi
else
    echo "ERROR: $TEST_BIN is not executable" >&2
    exit 1
fi
