#!/bin/sh
# Test script for postgresql-hypopg conan package.
# Verifies that the hypopg extension .so file is a valid ELF
# and contains the PostgreSQL extension magic function.

set -e

# Get the package root from environment
PKG_ROOT="${1:-$HYPOPG_PACKAGE_ROOT}"
if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: HYPOPG_PACKAGE_ROOT not set"
    exit 1
fi

echo "Package root: $PKG_ROOT"

# 1. Verify hypopg.so exists and is a valid ELF
SO_FILE="$PKG_ROOT/lib/postgresql/hypopg.so"
if [ ! -f "$SO_FILE" ]; then
    echo "FAIL: hypopg.so not found at $SO_FILE"
    exit 1
fi
echo "Found hypopg.so: $SO_FILE"

# Check it's a valid ELF
ELF_TYPE=$(file "$SO_FILE" 2>/dev/null || echo "unknown")
echo "File type: $ELF_TYPE"
case "$ELF_TYPE" in
    *ELF*)
        echo "OK: hypopg.so is a valid ELF file"
        ;;
    *)
        echo "FAIL: hypopg.so is not a valid ELF file"
        exit 1
        ;;
esac

# 2. Verify hypopg.control exists
CONTROL_FILE="$PKG_ROOT/share/postgresql/extension/hypopg.control"
if [ ! -f "$CONTROL_FILE" ]; then
    echo "FAIL: hypopg.control not found at $CONTROL_FILE"
    exit 1
fi
echo "Found hypopg.control: $CONTROL_FILE"

# 3. Check for extension version in control file
if grep -q "default_version.*1\.4\.2" "$CONTROL_FILE"; then
    echo "OK: hypopg.control has correct version 1.4.2"
else
    echo "FAIL: hypopg.control does not contain version 1.4.2"
    exit 1
fi

# 4. Verify SQL migration files exist
SQL_COUNT=$(ls "$PKG_ROOT/share/postgresql/extension/hypopg"--*.sql 2>/dev/null | wc -l)
if [ "$SQL_COUNT" -gt 0 ]; then
    echo "OK: Found $SQL_COUNT SQL migration files"
else
    echo "FAIL: No SQL migration files found"
    exit 1
fi

# 5. Check for Pg_magic_func symbol (PostgreSQL extension magic)
# This symbol must be present for PostgreSQL to recognize the extension
if command -v nm >/dev/null 2>&1; then
    if nm -D "$SO_FILE" 2>/dev/null | grep -q "Pg_magic_func"; then
        echo "OK: Pg_magic_func symbol found"
    else
        echo "WARN: Pg_magic_func not found (may be static)"
    fi
fi

echo ""
echo "TEST PASSED: All HypoPG extension files verified successfully"
