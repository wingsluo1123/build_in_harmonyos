#!/bin/sh
# smoke_test.sh — scrollz 2.2.3 test_package test source (L0c gate).
#
# Really runs the packaged `scrollz` binary and asserts observable output
# (not a stub that only prints strings). Upstream has no test suite at all,
# so this consumer-side smoke is the full verification:
#   T1: `scrollz --version` -> show_version() prints "ircII version <date>"
#       and exits 0 (parse_args() strips the leading dashes, then the `v`
#       switch fires before any terminal initialisation).
#   T2: `scrollz -v` -> the upstream single-dash version switch, same banner.
#
# Usage: sh smoke_test.sh <scrollz-binary>
# Exit:  0 = all assertions passed; 1 = assertion failed; 2 = usage error
set -u
BIN="${1:-}"

[ -n "$BIN" ] && [ -x "$BIN" ] || { echo "usage: $0 <scrollz-binary>"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi; }

echo "--- scrollz test_package smoke test ---"

# T1: --version banner + exit code 0
out=$("$BIN" --version 2>&1); rc=$?
printf '%s\n' "$out"
echo "$out" | grep -q "ircII version" && r=0 || r=1
chk "T1 scrollz --version prints 'ircII version ...' (rc=$rc)" "$r"
[ "$rc" = "0" ] && r=0 || r=1
chk "T1 scrollz --version exits 0" "$r"

# T2: -v banner (upstream single-dash form)
out=$("$BIN" -v 2>&1); rc=$?
echo "$out" | grep -q "ircII version" && r=0 || r=1
chk "T2 scrollz -v prints version banner (rc=$rc)" "$r"

if [ "$fail" = "0" ]; then
    echo "--- smoke test: ALL PASS ---"
else
    echo "--- smoke test: FAILED ---"
fi
exit $fail
