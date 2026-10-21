#!/bin/sh
# Consumer test driver for yorick-gl.
#
# Runs the *real* yorick interpreter in batch mode on the plugin test script
# and asserts both the process exit code and the success marker printed by the
# compiled plugin routine (arrlim3d), i.e. it depends on the built yorgl.so
# actually loading and executing.
#
# usage: test_yorick_gl.sh <yorick-binary> <yorick-test-script.i>
set -u

YORICK="$1"
SCRIPT="$2"

echo "--- yorick-gl consumer verification (headless plugin load + API call) ---"

out=$("$YORICK" -batch "$SCRIPT" 2>&1)
rc=$?
echo "$out"

if [ "$rc" != "0" ]; then
  echo "FAIL: yorick -batch $SCRIPT exit=$rc"
  exit 1
fi

if ! printf '%s\n' "$out" | grep -q "YORICKGL_CONSUMER_OK"; then
  echo "FAIL: expected marker YORICKGL_CONSUMER_OK not found in yorick output"
  exit 1
fi

echo "PASS: yorgl.so loaded by yorick, compiled yiso3d API (PrepIsoTet/MakeContourTree) verified: 1/1 script PASS"
exit 0
