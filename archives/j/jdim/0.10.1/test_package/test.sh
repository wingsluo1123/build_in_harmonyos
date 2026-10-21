#!/bin/sh
# test_package/test.sh — consumer test for the jdim application package.
#
# Runs the installed `jdim` binary and asserts its --version contract:
#   1. program name
#   2. upstream version 0.10.1
#   3. the configure switches this recipe passes (they are printed verbatim
#      from the buildinfo.h captured at configure time, so this is evidence
#      that the feature switches really reached configure)
set -eu

BIN="$1"

if [ ! -x "$BIN" ]; then
    echo "[fail] not executable: $BIN"
    exit 1
fi

OUT="$(timeout 120 "$BIN" --version 2>&1)" || {
    echo "[fail] 'jdim --version' exited non-zero"
    echo "$OUT"
    exit 1
}
echo "--- jdim --version ---"
echo "$OUT"
echo "----------------------"

check() {
    case "$OUT" in
        *"$1"*) echo "[ok] $1" ;;
        *) echo "[fail] --version output does not contain: $1"; exit 1 ;;
    esac
}

check "JDim"
check "0.10.1"
check "with-sessionlib=xsmp"
check "with-migemo"
check "with-alsa"

echo "[ok] jdim consumer test passed (5 assertions)"
