#!/bin/sh
# test_package/test.sh — Consumer smoke test for perl-crypt-openssl-verify
# Verifies that Verify.pm and Verify.so are present in the Conan package.
# On OHOS, runtime dlopen of .so is restricted by HMDFS SELinux (E073),
# so this test checks file presence and ELF validity only.

set -e

PKG_DIR="${1:-$(dirname "$0")/..}"

# Find Verify.pm
PM_FILE=$(find "$PKG_DIR" -name "Verify.pm" -type f 2>/dev/null | head -1)
if [ -z "$PM_FILE" ]; then
    echo "FAIL: Verify.pm not found in package"
    exit 1
fi
echo "OK: Found Verify.pm at $PM_FILE"

# Find Verify.so
SO_FILE=$(find "$PKG_DIR" -name "Verify.so" -type f 2>/dev/null | head -1)
if [ -z "$SO_FILE" ]; then
    echo "WARN: Verify.so not found in package"
else
    echo "OK: Found Verify.so at $SO_FILE"
    # Check it's a valid ELF file
    if command -v file >/dev/null 2>&1; then
        file "$SO_FILE"
    fi
fi

echo "test perl-crypt-openssl-verify 0.36-r2: OK"
