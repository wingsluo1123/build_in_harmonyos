#!/bin/sh
# test_package/test.sh — consumer smoke test for the packaged foolsm binary.
# Called by conanfile.py test() with the binary path as $1.
# foolsm -h/-v/--help print "version X" + usage and exit 2 (see usage.c).
set -eu

FOOLSM="${1:-foolsm}"
TOTAL=3
PASSED=0

fail_test() {
  printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"foolsm consumer smoke\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
  exit 1
}

if [ ! -x "$FOOLSM" ]; then
  echo "FAIL: foolsm binary not found or not executable: $FOOLSM"
  fail_test
fi
echo "PASS: foolsm binary found and executable"
PASSED=$((PASSED + 1))

# 1) foolsm -h prints version + usage, exits 2.
set +e
H_OUT=$("$FOOLSM" -h 2>&1)
H_RC=$?
set -e
echo "$H_OUT"
[ "$H_RC" -eq 2 ] || { echo "FAIL: foolsm -h exited $H_RC, expected 2"; fail_test; }
echo "$H_OUT" | grep -F "version 1.0.21" >/dev/null || { echo "FAIL: foolsm -h missing version string"; fail_test; }
echo "$H_OUT" | grep -F "usage:" >/dev/null || { echo "FAIL: foolsm -h missing usage text"; fail_test; }
echo "PASS: foolsm -h reports version 1.0.21 and usage"
PASSED=$((PASSED + 1))

# 2) foolsm -v behaves the same (version + usage, exit 2).
set +e
V_OUT=$("$FOOLSM" -v 2>&1)
V_RC=$?
set -e
echo "$V_OUT" | grep -F "version 1.0.21" >/dev/null || { echo "FAIL: foolsm -v missing version string"; fail_test; }
[ "$V_RC" -eq 2 ] || { echo "FAIL: foolsm -v exited $V_RC, expected 2"; fail_test; }
echo "PASS: foolsm -v reports version 1.0.21"
PASSED=$((PASSED + 1))

printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"foolsm consumer smoke\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
