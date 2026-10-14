#!/bin/sh
# test_package/test_osdmixer.sh - smoke test for the osdmixer executable.
# Usage: test_osdmixer.sh <path-to-osdmixer-binary>
# Invoked by conanfile.py with the packaged binary's full path.
#
# Full operation needs OSS /dev/mixer plus an X server for xosd, which a
# headless package test cannot rely on. The help path (fewer than 5
# arguments) still proves the binary executes: main() prints the version
# banner and usage text and exits 0 *before* opening /dev/mixer or creating
# any xosd object. Never invoke with 5 arguments: that enters the infinite
# mixer-monitor loop.
# Five deterministic assertions, one RESULT trailer for machine parsing.
set -u

OSDMIXER="${1:?usage: test_osdmixer.sh <osdmixer binary>}"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "[ok] $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "[fail] $1"
}

if [ ! -x "$OSDMIXER" ]; then
    bad "osdmixer binary not executable: $OSDMIXER"
    echo "RESULT: $PASS passed, $FAIL failed"
    exit 1
fi
ok "osdmixer binary is executable"

OUT1="$("$OSDMIXER" 2>&1)"
RC1=$?
echo "[test] bare osdmixer rc=$RC1"
echo "$OUT1" | head -8
if [ "$RC1" -eq 0 ]; then
    ok "bare osdmixer exits 0 on help path"
else
    bad "bare osdmixer exits 0 on help path (got rc=$RC1)"
fi

if [ -n "$OUT1" ]; then
    ok "help output is non-empty"
else
    bad "help output is non-empty (got empty output)"
fi

case "$OUT1" in
    *"osdmixer version 0.9"*)
        ok "help output contains the version banner"
        ;;
    *)
        bad "help output contains the version banner"
        ;;
esac

OUT2="$("$OSDMIXER" 48 48 2>&1)"
RC2=$?
echo "[test] osdmixer 48 48 rc=$RC2"
if [ "$RC2" -eq 0 ]; then
    ok "partial-args run exits 0 on help path"
else
    bad "partial-args run exits 0 on help path (got rc=$RC2)"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
