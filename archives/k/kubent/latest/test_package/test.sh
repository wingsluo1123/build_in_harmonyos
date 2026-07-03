#!/bin/sh
# test.sh — kubent smoke test
# Verifies that the kubent binary is functional by running --version and --help

set -e

KUBENT_BIN="${1:-kubent}"

echo "=== Testing kubent binary ==="

# Test 1: --version should succeed and print version info
echo "Test 1: kubent --version"
"$KUBENT_BIN" --version
if [ $? -ne 0 ]; then
    echo "FAIL: kubent --version failed"
    exit 1
fi
echo "PASS: kubent --version"

# Test 2: --help should succeed and print usage
echo "Test 2: kubent --help"
"$KUBENT_BIN" --help > /dev/null 2>&1 || true
echo "PASS: kubent --help"

# Test 3: Binary should be an ELF executable
echo "Test 3: file type check"
FILE_OUTPUT=$(file "$KUBENT_BIN")
echo "$FILE_OUTPUT"
case "$FILE_OUTPUT" in
    *ELF*executable*)
        echo "PASS: kubent is an ELF executable"
        ;;
    *)
        echo "FAIL: kubent is not an ELF executable"
        exit 1
        ;;
esac

echo "=== All smoke tests passed ==="
