#!/bin/sh
# test_crosstool.sh — functional smoke test for the crosstool (ct-ng) driver.
# Performs 4 real invocations of CT_NG_BIN and prints a deterministic
# "RESULT: P passed, F failed" trailer (parsed into HMBS evidence).
# Each case asserts exit status 0 AND an expected output substring, so an
# empty/mocked binary cannot fake a pass. POSIX sh only, no bashisms.
set -u

CT_NG_BIN="${CT_NG_BIN:?CT_NG_BIN must be set by test_package}"
WORK="${TMPDIR:-/tmp}/ct-ng-test-$$"
mkdir -p "$WORK"
PASS=0
FAIL=0

run_case() {
    _name="$1"
    _expect="$2"
    shift 2
    _out="$WORK/${_name}.out"
    if "$@" >"$_out" 2>&1; then
        if [ -s "$_out" ] && grep -qF "$_expect" "$_out"; then
            echo "PASS: $_name"
            PASS=$((PASS + 1))
        else
            echo "FAIL: $_name (output mismatch)"
            cat "$_out"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: $_name (non-zero exit)"
        cat "$_out"
        FAIL=$((FAIL + 1))
    fi
}

# 1. version action prints the real package version (ct-ng --version would
# print the make version instead: unknown args fall through to make).
run_case version "crosstool-NG version 1.28.0" "$CT_NG_BIN" version

# 2. help lists the configuration actions (needs no .config).
run_case help "menuconfig" "$CT_NG_BIN" help

# 3. list-steps enumerates the toolchain build steps (exercises make data).
run_case list-steps "binutils_for_host" "$CT_NG_BIN" list-steps

# 4. clean in an isolated dir (exercises a state-changing action safely).
mkdir -p "$WORK/cleanroom"
cd "$WORK/cleanroom"
run_case clean "CLEAN" "$CT_NG_BIN" clean

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
