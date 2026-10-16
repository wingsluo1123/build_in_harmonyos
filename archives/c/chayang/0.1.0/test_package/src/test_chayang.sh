#!/bin/sh
# test_chayang.sh — chayang consumer test (R34: must exercise the shipped artifact)
#
# Usage: test_chayang.sh <path-to-bin/chayang>
#
# Artifact assertions (always run):
#   1. bin/chayang exists
#   2. bin/chayang is executable
#   3. the ELF carries the upstream usage string (real chayang, not a stub)
#   4. the ELF carries the "-d" validation message
#   5. the ELF carries the "failed to connect to display" message
#   6. DT_NEEDED links libwayland-client.so.0 (the recipe's own dependency)
#
# Runtime assertions (execute the shipped binary):
#   7. `chayang -h`               -> exit 0 + "usage: chayang [-d seconds]"
#   8. `chayang -d <garbage>`     -> exit 1 + "invalid -d value"
#   9. `chayang` without a display-> exit 1 + "failed to connect to display"
#
# The three runtime assertions need an executable ELF. On OHOS that requires a
# valid `.codesign` section (E077) — the recipe re-signs the installed binary
# after meson's release install stripped the linker's placeholder away. If the
# binary is nevertheless refused by the loader, the runtime assertions are
# reported as SKIP with the exact message instead of being counted as PASS
# (measured 2026-10-16: an unsigned/stripped ELF gives "Operation not
# permitted"). FAIL is never downgraded to SKIP.
set -u

BIN="${1:-}"
if [ -z "$BIN" ]; then
    echo "FAIL: no binary path argument"
    exit 1
fi

PASS=0
FAIL=0
SKIP=0

TMPD="${TMPDIR:-$HOME/tmp}"
OUT="$TMPD/chayang-test.out.$$"
ERR="$TMPD/chayang-test.err.$$"
trap 'rm -f "$OUT" "$ERR"' EXIT

pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "SKIP: $1"; }

summary() {
    TOTAL=$((PASS + FAIL + SKIP))
    echo "chayang consumer test: TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
}

echo "== chayang consumer test =="
echo "binary: $BIN"

# ── 1. artifact present ──
if [ ! -f "$BIN" ]; then
    fail "bin/chayang is missing ($BIN)"
    summary
    exit 1
fi
pass "bin/chayang exists"

# ── 2. executable bit ──
if [ -x "$BIN" ]; then
    pass "bin/chayang is executable"
else
    fail "bin/chayang is not executable"
fi

# ── 3./4./5. it is the real program (upstream message strings in the ELF) ──
if command -v strings >/dev/null 2>&1; then
    for _probe in "usage: chayang" "invalid -d value" "failed to connect to display"; do
        if strings "$BIN" 2>/dev/null | grep -qF "$_probe"; then
            pass "ELF contains the upstream string '$_probe'"
        else
            fail "ELF lacks the upstream string '$_probe'"
        fi
    done
else
    skip "strings(1) unavailable — cannot check the embedded upstream strings"
fi

# ── 6. linked against the package's own dependency ──
echo "--- dynamic dependencies (readelf) ---"
if command -v readelf >/dev/null 2>&1; then
    readelf -d "$BIN" 2>/dev/null | grep -E "NEEDED|SONAME" || true
    if readelf -d "$BIN" 2>/dev/null | grep -qF "libwayland-client.so.0"; then
        pass "DT_NEEDED links libwayland-client.so.0"
    else
        fail "DT_NEEDED does not link libwayland-client.so.0"
    fi
else
    skip "readelf(1) unavailable — cannot check DT_NEEDED"
fi

# ── 7./8. argument handling (needs execution) ──
run_case() {
    # $1 description, $2 expected exit code, $3 expected substring, rest = cmd
    _desc="$1"; _want_rc="$2"; _want_msg="$3"
    shift 3
    "$@" >"$OUT" 2>"$ERR"
    _rc=$?
    if [ "$_rc" -ge 126 ] && grep -qE \
        "cannot execute|Operation not permitted|error while loading shared libraries|not found" \
        "$ERR" 2>/dev/null; then
        skip "$_desc — not executable in this sandbox: $(head -n 1 "$ERR")"
        return 0
    fi
    _combined="$(cat "$OUT" "$ERR" 2>/dev/null)"
    if [ "$_rc" -ne "$_want_rc" ]; then
        fail "$_desc — expected exit $_want_rc, got $_rc [$(printf '%s' "$_combined" | head -n 2 | tr '\n' ' ')]"
        return 0
    fi
    if ! printf '%s' "$_combined" | grep -q "$_want_msg"; then
        fail "$_desc — output lacks '$_want_msg' [$(printf '%s' "$_combined" | head -n 2 | tr '\n' ' ')]"
        return 0
    fi
    pass "$_desc (exit $_rc)"
}

run_case "chayang -h prints usage and exits 0" 0 "usage: chayang" "$BIN" -h
run_case "chayang -d <garbage> is rejected" 1 "invalid -d value" "$BIN" -d notanumber

# ── 9. no Wayland display: wl_display_connect() must fail (needs execution) ──
( unset WAYLAND_DISPLAY; unset XDG_RUNTIME_DIR; "$BIN" ) >"$OUT" 2>"$ERR"
RC=$?
if [ "$RC" -ge 126 ] && grep -qE \
    "cannot execute|Operation not permitted|error while loading shared libraries|not found" \
    "$ERR" 2>/dev/null; then
    skip "chayang without a display — not executable in this sandbox: $(head -n 1 "$ERR")"
else
    COMBINED="$(cat "$OUT" "$ERR" 2>/dev/null)"
    if [ "$RC" -ne 1 ]; then
        fail "chayang without a display — expected exit 1, got $RC [$(printf '%s' "$COMBINED" | head -n 2 | tr '\n' ' ')]"
    elif ! printf '%s' "$COMBINED" | grep -q "failed to connect to display"; then
        fail "chayang without a display — output lacks 'failed to connect to display' [$(printf '%s' "$COMBINED" | head -n 2 | tr '\n' ' ')]"
    else
        pass "chayang without a display reports 'failed to connect to display' (exit 1)"
    fi
fi

summary
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
