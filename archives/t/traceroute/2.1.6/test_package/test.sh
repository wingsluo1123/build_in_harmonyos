#!/data/service/hnp/bin/bash
# test.sh — test_package for traceroute 2.1.6
# Verifies the traceroute binary is installed and runs correctly.
set -e

# Run traceroute --version to verify the binary works
output=$(traceroute --version 2>&1)
echo "$output"

# Check that output contains expected version string
if echo "$output" | grep -q "2.1.6"; then
    echo "TEST PASSED: traceroute version 2.1.6 confirmed"
else
    echo "TEST FAILED: unexpected version output"
    exit 1
fi
