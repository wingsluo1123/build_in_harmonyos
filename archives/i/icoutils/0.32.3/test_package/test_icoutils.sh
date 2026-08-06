#!/bin/sh
# test_icoutils.sh — Verify icoutils binaries work correctly
# Called by test_package/conanfile.py
# R34: Tests the actual installed binary
set -euo pipefail

# Find icotool in PATH (conanrun env sets it up)
ICOTOOL=$(command -v icotool)
if [ -z "$ICOTOOL" ]; then
    echo "ERROR: icotool not found in PATH"
    exit 1
fi

# Verify version output contains expected string
VERSION_OUTPUT=$(icotool --version 2>&1)
if echo "$VERSION_OUTPUT" | grep -q "0.32.3"; then
    echo "PASS: icotool --version reports 0.32.3"
else
    echo "FAIL: icotool --version did not report 0.32.3"
    echo "Got: $VERSION_OUTPUT"
    exit 1
fi

# Verify wrestool also works
WRESTOOL_OUTPUT=$(wrestool --version 2>&1)
if echo "$WRESTOOL_OUTPUT" | grep -q "0.32.3"; then
    echo "PASS: wrestool --version reports 0.32.3"
else
    echo "FAIL: wrestool --version did not report 0.32.3"
    echo "Got: $WRESTOOL_OUTPUT"
    exit 1
fi

echo "All icoutils tests passed"
