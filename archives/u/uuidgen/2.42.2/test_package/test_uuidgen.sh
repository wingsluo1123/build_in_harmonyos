#!/bin/sh
# Consumer checks for the packaged uuidgen command.
#
# Usage: test_uuidgen.sh <path-to-uuidgen>
set -eu

BIN="$1"
[ -n "$BIN" ] || { echo "usage: $0 <uuidgen>" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: uuidgen is not executable: $BIN" >&2; exit 1; }

TMP="${TMPDIR:-$PWD}"
OUT="$TMP/uuidgen-check.out"
ERR="$TMP/uuidgen-check.err"
EXP="$TMP/uuidgen-check.expected"
trap 'rm -f "$OUT" "$ERR" "$EXP"' EXIT

ok=0
fail=0

check_flag() {
    flag="$1"
    if "$BIN" "$flag" > "$OUT" 2> "$ERR"; then
        if grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' "$OUT"; then
            ok=$((ok + 1))
            return 0
        fi
    fi
    echo "FAIL: uuidgen $flag did not emit a canonical UUID" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
}

check_oid() {
    args="$1"
    expected="$2"
    if "$BIN" $args > "$OUT" 2> "$ERR"; then
        printf '%s\n' "$expected" > "$EXP"
        if diff -u "$EXP" "$OUT" >/dev/null; then
            ok=$((ok + 1))
            return 0
        fi
        diff -u "$EXP" "$OUT" >&2 || true
    fi
    echo "FAIL: uuidgen $args did not emit the expected UUID" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
}

check_flag "-r"
check_flag "-t"
check_flag "-6"
check_flag "-7"
check_flag "--random"
check_flag "--time"
check_flag "--time-v6"
check_flag "--time-v7"

check_oid "--md5 --namespace @dns --name www.widgets.com" "3d813cbb-47fb-32ba-91df-831e1593ac29"
check_oid "--md5 --namespace @dns --name www.example.com" "5df41881-3aed-3515-88a7-2f4a814cf09e"
check_oid "--sha1 --namespace @dns --name www.example.com" "2ed6657d-e927-568b-95e1-2665a8aea6a2"
check_oid "--sha1 --namespace @oid --hex --name 525400fc0f5e" "fcdc2122-78d2-59f7-b1ed-041a561ef652"

echo "uuidgen consumer assertions: $ok passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
[ "$ok" -eq 12 ] || { echo "FAIL: expected 12 assertions, got $ok" >&2; exit 1; }
