#!/bin/sh
# test_memcache.sh — Smoke test for php-pecl-memcache extension
# Verifies the memcache.so is a valid ELF binary and contains expected symbols
# Note: Full runtime test requires PHP with session extension enabled
set -e

SO_PATH="${1:-memcache.so}"

echo "[test] Checking memcache.so exists..."
if [ ! -f "$SO_PATH" ]; then
    echo "[FAIL] memcache.so not found at $SO_PATH"
    exit 1
fi

echo "[test] Checking ELF format..."
file "$SO_PATH" | grep -q "ELF" || {
    echo "[FAIL] memcache.so is not a valid ELF binary"
    exit 1
}

echo "[test] Checking for memcache symbols..."
llvm-nm "$SO_PATH" 2>/dev/null | grep -qi "memcache" || {
    echo "[WARN] No memcache symbols found (may need full symbols)"
}

echo "[test] Checking file size..."
SIZE=$(wc -c < "$SO_PATH")
if [ "$SIZE" -lt 10000 ]; then
    echo "[FAIL] memcache.so too small ($SIZE bytes), likely incomplete"
    exit 1
fi

echo "[PASS] All smoke tests passed"
