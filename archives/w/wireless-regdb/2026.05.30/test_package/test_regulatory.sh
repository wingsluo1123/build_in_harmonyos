#!/usr/bin/env bash
# test_package/test_regulatory.sh — smoke test for wireless-regdb
# Verifies that regulatory database files are installed in the package.
set -euo pipefail

PKG_ROOT="${PKG_ROOT:-}"
if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: PKG_ROOT not set"
    exit 1
fi

# Check regulatory.db (firmware binary format)
DB_FILE="$PKG_ROOT/lib/firmware/regulatory.db"
if [ -f "$DB_FILE" ]; then
    SIZE=$(wc -c < "$DB_FILE")
    echo "OK: regulatory.db found ($SIZE bytes) at $DB_FILE"
else
    echo "FAIL: regulatory.db not found at $DB_FILE"
    exit 1
fi

# Check regulatory.db.p7s (signature)
P7S_FILE="$PKG_ROOT/lib/firmware/regulatory.db.p7s"
if [ -f "$P7S_FILE" ]; then
    SIZE=$(wc -c < "$P7S_FILE")
    echo "OK: regulatory.db.p7s found ($SIZE bytes) at $P7S_FILE"
else
    echo "FAIL: regulatory.db.p7s not found at $P7S_FILE"
    exit 1
fi

# Check regulatory.bin (crda legacy format)
BIN_FILE="$PKG_ROOT/usr/lib/crda/regulatory.bin"
if [ -f "$BIN_FILE" ]; then
    SIZE=$(wc -c < "$BIN_FILE")
    echo "OK: regulatory.bin found ($SIZE bytes) at $BIN_FILE"
else
    echo "FAIL: regulatory.bin not found at $BIN_FILE"
    exit 1
fi

echo "[test] wireless-regdb smoke test: PASS"
