#!/usr/bin/env bash
set -euo pipefail

# c-blosc2 test_package verification script
# Usage: test.sh [path/to/test_package_binary]

TEST_BIN="${1:-test_package}"

# Verify the test binary exists
test -f "$TEST_BIN"

# If the binary is executable, run it and verify output
if [ -x "$TEST_BIN" ]; then
    output=$("$TEST_BIN")
    echo "$output" | grep -q "Successful roundtrip!"
fi
