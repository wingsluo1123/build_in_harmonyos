#!/bin/bash
# cryptokit 1.21.1 smoke test - verify compiled C stubs
set -e

TEST_DIR="$(dirname "$0")"
PKG_DIR="${CONAN_PACKAGE_FOLDER:-$TEST_DIR/..}"

echo "=== cryptokit 1.21.1 C stubs verification ==="

# Check that the lib directory has compiled .o files
LIB_DIR="$PKG_DIR/lib"
if [ -d "$LIB_DIR" ]; then
    O_COUNT=$(find "$LIB_DIR" -name '*.o' 2>/dev/null | wc -l)
    echo "Compiled objects found: $O_COUNT"
    if [ "$O_COUNT" -eq 0 ]; then
        echo "FAIL: No compiled .o files found"
        exit 1
    fi
else
    echo "FAIL: lib directory not found"
    exit 1
fi

# Check header files
INC_DIR="$PKG_DIR/include/cryptokit"
if [ -d "$INC_DIR" ]; then
    H_COUNT=$(find "$INC_DIR" -name '*.h' 2>/dev/null | wc -l)
    echo "Header files found: $H_COUNT"
    if [ "$H_COUNT" -eq 0 ]; then
        echo "FAIL: No header files found"
        exit 1
    fi
else
    echo "FAIL: include/cryptokit directory not found"
    exit 1
fi

echo "=== cryptokit C stubs verification PASSED ==="
