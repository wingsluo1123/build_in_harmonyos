#!/data/service/hnp/bin/bash
# test.sh — par 1.53.0 smoke test
# Verifies that par binary is installed and functional.
set -euo pipefail

# par uses boolean option 'version', not --version
output=$(echo "" | par version 2>&1)
if [ "$output" != "par 1.53.0" ]; then
    echo "FAIL: version check failed, got: $output"
    exit 1
fi
echo "PASS: version check"

# Basic paragraph reflow
output=$(echo "Hello world test paragraph for reflow" | par 2>&1)
if [ -z "$output" ]; then
    echo "FAIL: reflow produced empty output"
    exit 1
fi
echo "PASS: paragraph reflow"

echo "All tests passed."
