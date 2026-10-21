#!/bin/sh
# Consumer checks for the packaged mcookie command.
#
# Usage: test_mcookie.sh <path-to-mcookie>
set -eu

BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <mcookie>" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: mcookie is not executable: $BIN" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/mcookie-check.XXXXXX")" || exit 1
OUT="$TMP/mcookie-check.out"
ERR="$TMP/mcookie-check.err"
SEED="$TMP/mcookie-check.seed"
trap 'rm -rf "$TMP"' EXIT

ok=0
fail=0

is_cookie() {
    # Accept either 32 lowercase hex chars (default) or 32 uppercase
    grep -Eq '^[0-9a-f]{32}$' "$OUT"
}

check_cookie_out() {
    label="$1"
    if is_cookie; then
        ok=$((ok + 1))
        return 0
    fi
    echo "FAIL: $label did not emit a 32-hex cookie" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
}

# 1. default invocation: no seed file, output must be 32 hex chars
if "$BIN" > "$OUT" 2> "$ERR"; then
    check_cookie_out "mcookie (default)"
else
    echo "FAIL: mcookie (default) exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

# 2. deterministic seed file via -f: still 32 hex chars
printf 'seed-data-for-mcookie-test\n' > "$SEED"
if "$BIN" -f "$SEED" > "$OUT" 2> "$ERR"; then
    check_cookie_out "mcookie -f <seed>"
else
    echo "FAIL: mcookie -f <seed> exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

# 3. -m limits how much is read from the seed file; must still succeed
if "$BIN" -m 16 -f "$SEED" > "$OUT" 2> "$ERR"; then
    check_cookie_out "mcookie -m 16 -f <seed>"
else
    echo "FAIL: mcookie -m 16 -f <seed> exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

# 4. verbose mode reports the byte counts on stderr
if "$BIN" -v -f "$SEED" > "$OUT" 2> "$ERR"; then
    if grep -Eq 'Got [0-9]+ byte' "$ERR"; then
        ok=$((ok + 1))
    else
        echo "FAIL: mcookie -v did not report byte counts on stderr" >&2
        cat "$ERR" >&2
        fail=$((fail + 1))
    fi
    check_cookie_out "mcookie -v -f <seed>"
else
    echo "FAIL: mcookie -v -f <seed> exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

# 5. --version identifies the util-linux release
if "$BIN" --version > "$OUT" 2> "$ERR"; then
    if grep -Eq '2\.42\.2' "$OUT"; then
        ok=$((ok + 1))
    else
        echo "FAIL: mcookie --version did not mention 2.42.2" >&2
        cat "$OUT" "$ERR" >&2
        fail=$((fail + 1))
    fi
else
    echo "FAIL: mcookie --version exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

# 6. missing seed file is a warning, not a fatal error: still exit 0 + 32 hex
#    (upstream misc-utils/mcookie.c: seed-file read failure only warns on
#    stderr and falls back to time-based seeding — asserted here as contract)
if "$BIN" -f /definitely/missing/mcookie-seed > "$OUT" 2> "$ERR"; then
    check_cookie_out "mcookie -f <missing-file>"
else
    echo "FAIL: mcookie -f <missing-file> exited nonzero" >&2
    cat "$ERR" >&2
    fail=$((fail + 1))
fi

echo "mcookie consumer assertions: $ok passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
[ "$ok" -eq 7 ] || { echo "FAIL: expected 7 assertions, got $ok" >&2; exit 1; }
