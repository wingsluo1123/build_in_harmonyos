#!/bin/sh
# Consumer end-to-end tests for the packaged snort 3.12.2.0 build.
#
# Usage: run_e2e.sh <snort-binary> <tests-dir>
#
# Every case is executed and judged independently; each prints exactly one
# "TEST PASS: <name>" or "TEST FAIL: <name>" line, and the run ends with a
# "TEST SUMMARY: N passed, M failed" line.  Any failure makes the script
# exit non-zero.
#
# The detection cases consume a deterministic synthetic capture that is
# generated at run time (gen_fixture.py); no binary fixture is tracked in the
# repository (ARCHIVE-SPEC: Git tracks recipes and knowledge, not binaries),
# so the tests stay self-contained.

set -u

SNORT="$1"
TESTS="$2"
PASS=0
FAIL=0

# OHOS /tmp is read-only; keep all temporaries under $HOME or the build cwd
: "${TMPDIR:=$HOME/tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || TMPDIR="$PWD"
export TMPDIR
WORK="$(mktemp -d "$TMPDIR/snort-e2e.XXXXXX" 2>/dev/null)" || WORK=""
[ -n "$WORK" ] || WORK="$PWD/snort-e2e-tmp"
mkdir -p "$WORK"

# Resolve the tests directory before any subshell changes the working directory.
case "$TESTS" in
    /*) ;;
    *) TESTS="$(cd "$TESTS" && pwd)" || exit 1 ;;
esac

# Generate the synthetic capture into the private work dir at test time — no
# binary fixture is committed by design (gitcode diffs carry no binary data).
FIXTURE="$WORK/fixture.pcap"
if ! (cd "$WORK" && python3 "$TESTS/gen_fixture.py") >"$WORK/gen_fixture.log" 2>&1; then
    echo "TEST SETUP FAIL: gen_fixture.py did not produce the capture; see $WORK/gen_fixture.log"
    sed 's/^/    | /' "$WORK/gen_fixture.log" 2>/dev/null | tail -15
    exit 1
fi

begin_case() {
    CASE_NAME="$1"
    CASE_OUT="$WORK/${CASE_NAME}.out"
}

end_case() {
    if [ "$1" -eq 0 ]; then
        echo "TEST PASS: $CASE_NAME"
        PASS=$((PASS + 1))
    else
        echo "TEST FAIL: $CASE_NAME (exit=$1)"
        sed 's/^/    | /' "$CASE_OUT" 2>/dev/null | tail -25
        FAIL=$((FAIL + 1))
    fi
}

ICMP_RULE='alert icmp any any -> any any (msg:"OHPC-E2E-ICMP"; sid:9000001; rev:1;)'
NEG_RULE='alert udp any any -> any 1 (msg:"OHPC-E2E-NEGATIVE"; sid:9000002; rev:1;)'

# --- case 1: version output --------------------------------------------------
begin_case "version_output"
"$SNORT" -V >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "3\.12\.2\.0" "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

# --- case 2: help output -----------------------------------------------------
begin_case "help_output"
"$SNORT" --help >"$CASE_OUT" 2>&1
rc=$?
# Multi-pattern via -e/-e: "\|" is a GNU BRE extension that other greps
# (e.g. toybox) treat literally, so the case must not rely on it.
if [ $rc -eq 0 ] && grep -qi -e usage -e snort "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

# --- case 3: configuration validation (-T) -----------------------------------
begin_case "config_validate"
"$SNORT" -T -c "$TESTS/min.lua" --rule "$ICMP_RULE" >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -qi "successfully validated" "$CASE_OUT"; then
    rc=0
else
    rc=1
fi
end_case $rc

# --- case 4: end-to-end detection over a crafted pcap (positive) -------------
begin_case "detect_icmp_positive"
"$SNORT" -c "$TESTS/min.lua" -q -A alert_fast --rule "$ICMP_RULE" \
    -r "$FIXTURE" >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "OHPC-E2E-ICMP" "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

# --- case 5: negative control (rule must NOT match the same pcap) ------------
begin_case "detect_negative_control"
"$SNORT" -c "$TESTS/min.lua" -q -A alert_fast --rule "$NEG_RULE" \
    -r "$FIXTURE" >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && ! grep -q "OHPC-E2E-NEGATIVE" "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

# --- case 6: embedded Catch2 suite -------------------------------------------
begin_case "catch2_embedded_suite"
"$SNORT" --catch-test all >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "All tests passed" "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

echo "TEST SUMMARY: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
