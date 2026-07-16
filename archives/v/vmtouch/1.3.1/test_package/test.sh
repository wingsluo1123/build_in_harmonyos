#!/bin/sh
# R34: Test must actually exercise the tested package's binary
# vmtouch is a CLI tool — test by running vmtouch -h and on a temp file
set -e

VMTOUCH_BIN="${1:-vmtouch}"

# L2 smoke test: verify binary runs and shows version
output=$("$VMTOUCH_BIN" -h 2>&1 || true)
case "$output" in
    *vmtouch*)
        echo "PASS: vmtouch binary works correctly"
        ;;
    *)
        echo "FAIL: unexpected output from vmtouch -h"
        echo "  output: $output"
        exit 1
        ;;
esac

# Functional test: run vmtouch on a temp file to verify cache inspection
_tmpdir="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_tmpdir" 2>/dev/null || true
tmpfile=$(mktemp "$_tmpdir/vmtouch_test_XXXXXX.txt")
echo "vmtouch test content" > "$tmpfile"
output=$("$VMTOUCH_BIN" "$tmpfile" 2>&1)
rm -f "$tmpfile"

case "$output" in
    *Pages*)
        echo "PASS: vmtouch file inspection works"
        ;;
    *)
        echo "FAIL: vmtouch did not inspect the file"
        echo "  output: $output"
        exit 1
        ;;
esac
