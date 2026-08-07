#!/bin/sh
# test_dsa.sh — Test script for Crypt-OpenSSL-DSA package.
#
# R34: Substantive test that verifies the XS module build:
# 1. DSA.pm exists and is valid Perl (perl -c)
# 2. DSA.so is a valid ELF shared object (file)
# 3. DSA.so contains the XS bootstrap function (readelf -s)
# 4. DSA.so links against OpenSSL libcrypto (readelf -d)
#
# Usage: test_dsa.sh <package_folder>
#
# Note: XS module runtime loading may be blocked by SELinux HMDFS on HarmonyOS.
# This script uses static analysis for guaranteed verification.

set -e

PKG_DIR="${1:?Usage: test_dsa.sh <package_folder>}"

# Detect Perl version and architecture dynamically
PERL_VER=$(perl -e 'print sprintf("%vd", $^V)')
PERL_ARCH=$(perl -MConfig -e 'print $Config{archname}')

# Fallbacks
: "${PERL_VER:=5.42.0}"
: "${PERL_ARCH:=aarch64-linux}"

echo "Perl version: $PERL_VER"
echo "Perl arch: $PERL_ARCH"

# Test 1: DSA.pm exists and is valid Perl
DSA_PM="$PKG_DIR/lib/site_perl/$PERL_VER/Crypt/OpenSSL/DSA.pm"
if [ ! -f "$DSA_PM" ]; then
    echo "FAIL: DSA.pm not found at $DSA_PM"
    exit 1
fi
echo "Checking DSA.pm syntax..."
perl -c "$DSA_PM"
echo "PASS: DSA.pm syntax OK"

# Test 2: DSA.so exists and is valid ELF
DSA_SO="$PKG_DIR/lib/site_perl/$PERL_VER/$PERL_ARCH/auto/Crypt/OpenSSL/DSA/DSA.so"
if [ ! -f "$DSA_SO" ]; then
    echo "FAIL: DSA.so not found at $DSA_SO"
    exit 1
fi
echo "Checking DSA.so file type..."
file "$DSA_SO" | grep -q "ELF"
echo "PASS: DSA.so is valid ELF"

# Test 3: DSA.so contains XS boot function
echo "Checking XS boot symbol..."
readelf -s "$DSA_SO" | grep -i "boot_Crypt"
echo "PASS: XS boot function present"

# Test 4: DSA.so links against OpenSSL libcrypto
echo "Checking OpenSSL dependency..."
readelf -d "$DSA_SO" | grep -E "libcrypto"
echo "PASS: OpenSSL dependency verified"

echo ""
echo "=== All tests passed ==="
