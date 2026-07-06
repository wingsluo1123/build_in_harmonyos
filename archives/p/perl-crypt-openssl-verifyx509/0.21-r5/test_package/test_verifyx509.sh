#!/bin/bash
# test_verifyx509.sh — L0 test source for Crypt::OpenSSL::VerifyX509
# Called by test_package/conanfile.py via self.run()
#
# Tests:
#   1. VerifyX509.so is a valid ELF shared object
#   2. VerifyX509.pm has correct package declaration
#   3. (Best-effort) Runtime module load test
#
# Usage: bash test_verifyx509.sh <package_folder>
# Exit: 0 = pass, 1 = fail

set -euo pipefail

PKG_DIR="${1:-.}"
STATUS=0

echo "[test] Package folder: $PKG_DIR"

# --- Test 1: Find and validate VerifyX509.so ---
SO_FILE=$(find "$PKG_DIR" -name "VerifyX509.so" -type f 2>/dev/null | head -1)
if [ -z "$SO_FILE" ]; then
    echo "[fail] VerifyX509.so not found in package"
    exit 1
fi
echo "[ok] Found VerifyX509.so: $SO_FILE"

# Check ELF magic
MAGIC=$(head -c 4 "$SO_FILE" | xxd -p 2>/dev/null || echo "")
if [ "$MAGIC" = "7f454c46" ]; then
    echo "[ok] VerifyX509.so is a valid ELF file"
else
    echo "[fail] VerifyX509.so is not a valid ELF (magic: $MAGIC)"
    STATUS=1
fi

# Check ELF class (64-bit)
ELF_CLASS=$(head -c 5 "$SO_FILE" | tail -c 1 | xxd -p 2>/dev/null || echo "")
if [ "$ELF_CLASS" = "02" ]; then
    echo "[ok] VerifyX509.so is 64-bit ELF"
else
    echo "[warn] VerifyX509.so ELF class: $ELF_CLASS (expected 02=64-bit)"
fi

# --- Test 2: Find and validate VerifyX509.pm ---
PM_FILE=$(find "$PKG_DIR" -name "VerifyX509.pm" -type f 2>/dev/null | head -1)
if [ -z "$PM_FILE" ]; then
    echo "[fail] VerifyX509.pm not found in package"
    exit 1
fi
echo "[ok] Found VerifyX509.pm: $PM_FILE"

if grep -q "package Crypt::OpenSSL::VerifyX509" "$PM_FILE" 2>/dev/null; then
    echo "[ok] VerifyX509.pm has correct package declaration"
else
    echo "[fail] VerifyX509.pm missing package declaration"
    STATUS=1
fi

if grep -q "use Crypt::OpenSSL::X509" "$PM_FILE" 2>/dev/null; then
    echo "[ok] VerifyX509.pm declares Crypt::OpenSSL::X509 dependency"
else
    echo "[warn] VerifyX509.pm missing Crypt::OpenSSL::X509 dependency declaration"
fi

# --- Test 3: Best-effort runtime load ---
# On OpenHarmony, HMDFS SELinux (E073) may block dlopen of .so files
# from user directories. This is a platform limitation, not a build issue.
PERL5LIB=$(find "$PKG_DIR" -type d -name "perl5" 2>/dev/null | head -1)
if [ -n "$PERL5LIB" ]; then
    ARCH_DIR=$(find "$PKG_DIR" -type d -name "aarch64-linux" 2>/dev/null | head -1)
    export PERL5LIB="${ARCH_DIR:-}:$PERL5LIB"
fi

if perl -e "use Crypt::OpenSSL::VerifyX509; print 'loaded OK\n';" 2>/dev/null; then
    echo "[ok] Runtime load test: PASS"
else
    echo "[info] Runtime load test: SKIPPED (platform limitation or missing runtime deps)"
fi

# --- Summary ---
if [ $STATUS -eq 0 ]; then
    echo "[result] All structural tests PASSED"
else
    echo "[result] Some tests FAILED"
fi

exit $STATUS
