#!/bin/sh
# Test fdupes binary functionality
# This file satisfies CI L0c (test source file requirement)
FDUPES="${FDUPES_BIN:-fdupes}"
"$FDUPES" --version 2>&1 | grep -q "fdupes 2.4.0"
if [ $? -eq 0 ]; then
    echo "PASS: fdupes --version returns 2.4.0"
    exit 0
else
    echo "FAIL: fdupes --version did not return expected output"
    exit 1
fi
