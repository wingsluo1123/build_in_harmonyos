#!/bin/sh
# test_package/test_ax25ipd.sh — R34: Execute the packaged binary
# This script runs ax25ipd --version to verify the binary is functional.
# Called by test_package/conanfile.py test() method.

set -euo pipefail 2>/dev/null || set -eu

AX25IPD="${1:-ax25ipd}"
"$AX25IPD" --version 2>&1
if [ $? -eq 0 ]; then
    echo "TEST PASSED: ax25ipd --version returned 0"
    exit 0
else
    echo "TEST FAILED: ax25ipd --version returned non-zero"
    exit 1
fi
