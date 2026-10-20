#!/bin/sh
# test_sniffit.sh — consumer functional test for the sniffit 0.7 package.
#
#   sh test_sniffit.sh <path-to-sniffit-binary> <workdir>
#
# Runs the installed bin/sniffit binary through 5 real invocations that need
# no privileges and open no network device, then prints a machine-readable
# "RESULT: P passed, F failed" trailer line, which test_package/conanfile.py
# parses into HMBS_TEST_PACKAGE_RESULT.
#
# Case plan (see notes.md problem 4/5 for why these exact probes):
#   1. Binary inventory: present, executable, non-empty.
#   2. `sniffit -v` exits 0 (upstream quit() path, works without root).
#   3. `sniffit -v` output is non-empty and carries the exact contract
#      "Sniffit Version 0.7" (musl loader errors cannot match this).
#   4. Bare `sniffit` prints real app text in both privilege contexts:
#      root -> usage() ("usage:"); non-root -> "You should be root".
#      Either is accepted, but empty output is a failure (anti-empty-run).
#   5. Negative control: `sniffit -t <invalid-host>` must FAIL (exit != 0)
#      with non-empty app text ("Non existing host!" as root, or the root
#      warning as non-root), proving the harness observes real failures.
#
# Upstream ships no test suite; this validates the packaged application.

set -u

BIN="$1"
WORKDIR="$2"

# Device HMFS /tmp may be read-only: prefer the HMBS-injected writable
# TMPDIR/TMP/TEMP, fall back to <workdir> (never a hardcoded /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
mkdir -p "$_TMPBASE" 2>/dev/null || _TMPBASE="$WORKDIR"
mkdir -p "$WORKDIR" 2>/dev/null || true
OUT="$_TMPBASE/sniffit-test-out.txt"
PASS=0
FAIL=0

report() {
    # $1 = case number, $2 = ok (0/1), $3 = label
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    # $1 = exit code; print bounded output excerpt for diagnosis.
    # (Exit code alone cannot distinguish a loader failure from an app error.)
    echo "  exit=$1, output excerpt (first 12 lines of $OUT):"
    sed -n '1,12p' "$OUT" 2>/dev/null || echo "  (no output file)"
}

# --- Case 1: binary present, executable, non-empty ------------------------
if [ -x "$BIN" ] && [ -s "$BIN" ]; then
    report 1 0 "sniffit binary present, executable and non-empty"
else
    echo "  path checked: $BIN"
    ls -l "$BIN" 2>/dev/null || echo "  (binary missing)"
    report 1 1 "binary inventory failed"
fi

# --- Case 2: `sniffit -v` exits 0 -----------------------------------------
"$BIN" -v > "$OUT" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    report 2 0 "sniffit -v exits 0"
else
    dump_out "$rc"
    report 2 1 "sniffit -v exited $rc"
fi

# --- Case 3: `-v` output carries the exact version contract ---------------
if [ -s "$OUT" ] && grep -q "Sniffit Version 0.7" "$OUT"; then
    report 3 0 "-v prints 'Sniffit Version 0.7'"
else
    dump_out "$rc"
    report 3 1 "-v output lacks the version contract"
fi

# --- Case 4: bare invocation prints real app text in both contexts -------
"$BIN" > "$OUT" 2>&1
rc=$?
if [ -s "$OUT" ] && { grep -qi "usage:" "$OUT" || grep -q "You should be root" "$OUT"; }; then
    report 4 0 "bare invocation prints usage (root) or privilege notice (non-root)"
else
    dump_out "$rc"
    report 4 1 "bare invocation produced no recognizable app text"
fi

# --- Case 5 (negative control): invalid target host must be rejected ------
"$BIN" -t definitely-not-a-real-host-12345.invalid > "$OUT" 2>&1
rc=$?
if [ "$rc" -ne 0 ] && [ -s "$OUT" ] && { grep -q "Non existing host" "$OUT" || grep -q "You should be root" "$OUT"; }; then
    report 5 0 "invalid host rejected with real app error (exit=$rc)"
else
    dump_out "$rc"
    report 5 1 "invalid host not rejected as expected (exit=$rc)"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
