#!/system/bin/sh
set -uo pipefail
# test_microsocks.sh - Verify microsocks binary is functional
# microsocks --help exits with code 1 and prints to stderr
# This script captures output and verifies the binary works
BIN="$1"
if [ -z "$BIN" ]; then
    echo "FAIL: no binary path provided"
    exit 1
fi

output=$("$BIN" --help 2>&1)
exit_code=$?

if echo "$output" | grep -q "MicroSocks"; then
    echo "test_microsocks: PASS (exit_code=$exit_code)"
    exit 0
else
    echo "test_microsocks: FAIL (output=$output)"
    exit 1
fi
