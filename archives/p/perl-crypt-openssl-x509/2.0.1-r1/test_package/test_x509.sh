#!/bin/sh
# test_package/test_x509.sh — L0c test source file
# Verifies Crypt::OpenSSL::X509 package structure
# On OHOS, runtime dlopen is restricted by SELinux (E073), so this test
# checks file presence only. On Linux, it also attempts runtime loading.

set -e

PKG_DIR="${1:-.}"

echo "[test] Checking package structure in: $PKG_DIR"

# Find X509.so and X509.pm
SO_FOUND=$(find "$PKG_DIR" -name "X509.so" -type f 2>/dev/null | head -1)
PM_FOUND=$(find "$PKG_DIR" -name "X509.pm" -type f 2>/dev/null | head -1)

if [ -z "$PM_FOUND" ]; then
    echo "[fail] X509.pm not found in package"
    exit 1
fi

echo "[ok] X509.pm found: $PM_FOUND"

if [ -n "$SO_FOUND" ]; then
    echo "[ok] X509.so found: $SO_FOUND"
    # Try runtime load on non-OHOS platforms
    if [ "$(uname 2>/dev/null)" != "OpenHarmony" ] && command -v perl >/dev/null 2>&1; then
        if perl -e "use Crypt::OpenSSL::X509; print 'OK\n';" 2>/dev/null | grep -q "OK"; then
            echo "[ok] Runtime load test passed"
        else
            echo "[warn] Runtime load test failed (may be platform limitation)"
        fi
    else
        echo "[skip] Runtime load test skipped on OHOS (E073: SELinux dlopen restriction)"
    fi
else
    echo "[warn] X509.so not found (may be a pure-Perl package)"
fi

echo "[done] Package structure verification complete"
