#!/bin/sh
# test.sh — Devel-Caller 2.07 consumer test (R34 compliant)
#
# Verifies Caller.so is a valid ELF shared library with the expected
# boot_Devel__Caller XS entry point symbol.
#
# Uses readelf instead of dlopen because Caller.so is a Perl XS module
# with unresolved Perl interpreter symbols that require the Perl
# runtime to resolve at load time.
SO_PATH="$1"

if [ -z "$SO_PATH" ]; then
    echo "FAIL: no .so path provided"
    exit 1
fi

if [ ! -f "$SO_PATH" ]; then
    echo "FAIL: $SO_PATH does not exist"
    exit 1
fi

# 1. Verify ELF format
if ! readelf -h "$SO_PATH" 2>/dev/null | grep -q "ELF"; then
    echo "FAIL: not a valid ELF"
    exit 1
fi

# 2. Verify boot_Devel__Caller XS entry point symbol exists
if ! readelf -s "$SO_PATH" 2>/dev/null | grep -q "boot_Devel__Caller"; then
    echo "FAIL: boot_Devel__Caller symbol not found"
    exit 1
fi

# 3. Verify NEEDED libc.so (only runtime dependency)
if ! readelf -d "$SO_PATH" 2>/dev/null | grep -q "libc.so"; then
    echo "FAIL: libc.so not in NEEDED"
    exit 1
fi

echo "OK: Caller.so verified (ELF + boot_Devel__Caller + libc.so)"
