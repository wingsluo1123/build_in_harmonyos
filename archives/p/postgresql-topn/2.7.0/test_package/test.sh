#!/bin/bash
# test.sh - Verify postgresql-topn package artifacts
# Called by test_package/conanfile.py test() method.

set -euo pipefail

PACKAGE_DIR="${1:-.}"
LIBDIR="$PACKAGE_DIR/lib/postgresql"
EXTDIR="$PACKAGE_DIR/share/postgresql/extension"

echo "[step] Checking topn.so..."
if [ ! -f "$LIBDIR/topn.so" ]; then
    echo "        [fail] topn.so not found at $LIBDIR/topn.so"
    exit 1
fi

echo "[step] Verifying ELF format..."
readelf -h "$LIBDIR/topn.so" > /dev/null 2>&1 || {
    echo "        [fail] topn.so is not a valid ELF file"
    exit 1
}

echo "[step] Checking topn.control..."
if [ ! -f "$EXTDIR/topn.control" ]; then
    echo "        [fail] topn.control not found"
    exit 1
fi

echo "[step] Checking SQL files..."
SQL_COUNT=$(find "$EXTDIR" -name 'topn--*.sql' -type f | wc -l)
if [ "$SQL_COUNT" -lt 1 ]; then
    echo "        [fail] No topn--*.sql files found"
    exit 1
fi
echo "        [ok] Found $SQL_COUNT SQL migration files"

echo "[step] Checking base migration topn--2.0.0.sql..."
if [ ! -f "$EXTDIR/topn--2.0.0.sql" ]; then
    echo "        [fail] topn--2.0.0.sql not found"
    exit 1
fi

echo "        [ok] All artifact checks passed"
exit 0
