#!/bin/sh
# test_silk.sh — consumer verification for SiLK 3.24.2.
# Usage: test_silk.sh <package-bin-dir>
# 3 assertions: rwcut / rwcount / silk_config --version report 3.24.2.
set -eu
BIN="$1"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$BIN/rwcut" ] || fail "rwcut not executable"
[ -x "$BIN/rwcount" ] || fail "rwcount not executable"
[ -x "$BIN/silk_config" ] || fail "silk_config not executable"
OUT1=$("$BIN/rwcut" --version 2>&1) || fail "rwcut --version rc=$?"
echo "$OUT1" | grep -q "3.24.2" || fail "rwcut version mismatch: $OUT1"
echo "ok1 rwcut $OUT1"
OUT2=$("$BIN/rwcount" --version 2>&1) || fail "rwcount --version rc=$?"
echo "$OUT2" | grep -q "3.24.2" || fail "rwcount version mismatch: $OUT2"
echo "ok2 rwcount $OUT2"
OUT3=$("$BIN/silk_config" --version 2>&1) || fail "silk_config --version rc=$?"
echo "$OUT3" | grep -q "3.24.2" || fail "silk_config version mismatch: $OUT3"
echo "ok3 silk_config $OUT3"
[ -n "$OUT1" ] && [ -n "$OUT2" ] && [ -n "$OUT3" ] || fail "empty version output"
echo "all 3 silk consumer tests passed"
