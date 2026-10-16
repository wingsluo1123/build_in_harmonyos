#!/bin/sh
# Consumer test wrapper for yorick: runs the installed interpreter in batch
# mode on test.i and asserts on its real output + exit code.
export PATH="$PATH:/system/bin"

echo "--- yorick consumer verification ---"

out=$(yorick -batch test.i 2>&1)
rc=$?
echo "$out"

[ "$rc" = "0" ] || { echo "FAIL: yorick -batch test.i exit=$rc"; exit 1; }

echo "$out" | grep -q "YORICK_CONSUMER_OK" || {
  echo "FAIL: expected marker YORICK_CONSUMER_OK not found"; exit 1; }

echo "PASS: yorick interpreter consumer checks (arith/array/matrix): 1/1 script PASS"
exit 0
