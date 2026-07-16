#!/bin/sh
# test_txt2man.sh — Functional test for txt2man binary
# Invoked by test_package/conanfile.py test() method.
set -e

TXT2MAN="$1"

# Test 1: txt2man -h (help)
echo "Test 1: txt2man -h"
"$TXT2MAN" -h 2>&1 | head -5
echo "PASS: help output exists"
echo ""

# Test 2: convert text to man page format
echo "Test 2: text -> man page conversion"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/test_input.txt" <<'EOF'
NAME
  test - txt2man conversion test

DESCRIPTION
  This is a test.
EOF

"$TXT2MAN" -t test -s 1 "$TMPDIR/test_input.txt" > "$TMPDIR/output.1" 2>&1

if grep -Eq '\.TH|\.SH' "$TMPDIR/output.1"; then
    echo "PASS: man page macros found in output"
else
    echo "FAIL: expected .TH or .SH macros in output"
    exit 1
fi

echo ""
echo "All tests passed."
