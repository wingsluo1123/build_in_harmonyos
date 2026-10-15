#!/bin/sh
# Consumer end-to-end tests for the packaged myMPD 25.3.0 build.
#
# Usage: run_e2e.sh <mympd-binary>
#
# Every case is executed and judged independently; each prints exactly one
# "TEST PASS: <name>" or "TEST FAIL: <name>" line, and the run ends with a
# "TEST SUMMARY: N passed, M failed" line.  Any failure makes the script
# exit non-zero.
#
# All cases are local and contact no network: version / help / default
# configuration dump, and the bootstrap (-c) that writes the per-item
# configuration files and generates the self-signed TLS certificates below
# a scratch work directory under $TMPDIR.

set -u

MYMPD="$1"
PASS=0
FAIL=0

# OHOS /tmp is read-only; keep all temporaries under $HOME or the cwd
: "${TMPDIR:=$HOME/tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || TMPDIR="$PWD"
export TMPDIR
WORK="$(mktemp -d "$TMPDIR/mympd-e2e.XXXXXX" 2>/dev/null)" || WORK=""
[ -n "$WORK" ] || WORK="$PWD/mympd-e2e-tmp"
mkdir -p "$WORK"

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

# --- case 1: version output --------------------------------------------------
begin_case "version_output"
"$MYMPD" -v >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "myMPD 25\.3\.0" "$CASE_OUT" \
    && grep -q "Libmpdclient 2\.26\.0 (embedded)" "$CASE_OUT"; then
    rc=0
else
    rc=1
fi
end_case $rc

# --- case 2: help output -----------------------------------------------------
begin_case "help_output"
"$MYMPD" -h >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "Usage:" "$CASE_OUT"; then rc=0; else rc=1; fi
end_case $rc

# --- case 3: default configuration dump --------------------------------------
begin_case "dump_default_config"
"$MYMPD" -d >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && grep -q "Default configuration:" "$CASE_OUT" \
    && grep -q "http_port: 8080" "$CASE_OUT"; then
    rc=0
else
    rc=1
fi
end_case $rc

# --- case 4: bootstrap writes the config tree and certificates ---------------
begin_case "bootstrap_config_and_certificates"
"$MYMPD" -c -w "$WORK/work" -a "$WORK/cache" >"$CASE_OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s "$WORK/work/config/http_port" ] \
    && [ -s "$WORK/work/ssl/ca.pem" ] && [ -s "$WORK/work/ssl/server.pem" ]; then
    rc=0
else
    rc=1
    {
        echo "---- files below the work directory ----"
        find "$WORK/work" -type f 2>/dev/null | head -30
    } >>"$CASE_OUT"
fi
end_case $rc

# --- case 5: negative control, an unknown option must fail gracefully --------
# A clean rejection exits with a small non-zero status; anything >= 128 is a
# fatal signal (e.g. a crash) and must not count as a rejection.
begin_case "negative_control_invalid_option"
"$MYMPD" --definitely-not-a-mympd-option >"$CASE_OUT" 2>&1
rc=$?
if [ "$rc" -gt 0 ] && [ "$rc" -lt 128 ]; then rc=0; else rc=1; fi
end_case $rc

echo "TEST SUMMARY: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
