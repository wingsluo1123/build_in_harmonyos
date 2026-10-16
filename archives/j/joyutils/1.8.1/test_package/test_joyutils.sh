#!/bin/sh
# test_joyutils.sh - consumer functional test for the joyutils 1.8.1 package.
# Runs the installed joystick binaries through real invocations and prints
# a machine-readable "RESULT: P passed, F failed" trailer line, which
# test_package/conanfile.py parses into HMBS_TEST_PACKAGE_RESULT.
# No joystick hardware is required: all cases use --help/usage paths and
# error paths that never touch /dev/js*.
# Case 4 is a negative control (nonexistent device must fail), proving the
# harness observes real failures instead of passing empty output.

set -u

JSTEST="${JSTEST_BIN:-jstest}"
JSCAL="${JSCAL_BIN:-jscal}"
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
OUT="$_TMPBASE/joyutils-test-out.txt"
PASS=0
FAIL=0

report() {
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    echo "  exit=$1, output excerpt (first 10 lines):"
    head -n 10 "$OUT" 2>/dev/null || echo "  (no output file)"
}

# Case 1: jstest --help exits 1 and prints usage.
"$JSTEST" --help > "$OUT" 2>&1
rc=$?
if [ $rc -eq 1 ]; then
    if grep -q "Usage: jstest" "$OUT" && [ -s "$OUT" ]; then
        report 1 0 "jstest --help prints usage"
    else
        dump_out $rc
        report 1 1 "jstest --help missing usage text"
    fi
else
    dump_out $rc
    report 1 1 "jstest --help exited $rc (expected 1)"
fi

# Case 2: jscal -h exits 0 and prints usage.
"$JSCAL" -h > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    if grep -q "Usage: jscal" "$OUT" && [ -s "$OUT" ]; then
        report 2 0 "jscal -h prints usage"
    else
        dump_out $rc
        report 2 1 "jscal -h missing usage text"
    fi
else
    dump_out $rc
    report 2 1 "jscal -h exited $rc (expected 0)"
fi

# Case 3: bare jscal exits 1 and prints usage.
"$JSCAL" > "$OUT" 2>&1
rc=$?
if [ $rc -eq 1 ]; then
    if grep -q "Usage: jscal" "$OUT" && [ -s "$OUT" ]; then
        report 3 0 "bare jscal prints usage"
    else
        dump_out $rc
        report 3 1 "bare jscal missing usage text"
    fi
else
    dump_out $rc
    report 3 1 "bare jscal exited $rc (expected 1)"
fi

# Case 4 (negative control): jstest on a nonexistent device must fail.
"$JSTEST" /dev/nonexistent-joytest-xyz > "$OUT" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    report 4 0 "jstest on missing device fails as expected"
else
    dump_out $rc
    report 4 1 "jstest on missing device unexpectedly succeeded"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
