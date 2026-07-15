#!/bin/sh
# Test source file for sloci-image test_package
# This script verifies that sloci-image is installed and functional.
#
# Usage: ./test_sloci_image.sh [path_to_sloci_image]

set -euo pipefail

SLOCI_IMAGE="${1:-sloci-image}"

# Test 1: Verify --version works
output=$("$SLOCI_IMAGE" --version)
case "$output" in
    sloci-image*)
        echo "PASS: --version returns correct format"
        ;;
    *)
        echo "FAIL: --version returned unexpected output: $output"
        exit 1
        ;;
esac

# Test 2: Verify --help works
"$SLOCI_IMAGE" --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "PASS: --help exits successfully"
else
    echo "FAIL: --help failed"
    exit 1
fi

echo "All tests passed."
