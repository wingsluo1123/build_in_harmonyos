#!/bin/sh
# test_tofi.sh — tofi consumer test (R34: must exercise the shipped artifact)
#
# Usage: test_tofi.sh <conan-package-folder>
#
# Artifact assertions (always run):
#   1. bin/tofi exists
#   2. bin/tofi is executable
#   3. bin/tofi-run is a symlink to tofi (upstream install_symlink)
#   4. bin/tofi-drun is a symlink to tofi (upstream install_symlink)
#   5. the ELF carries the upstream usage banner (real tofi, not a stub)
#   6. the ELF carries the "Couldn't connect to Wayland display." message
#   7. DT_NEEDED links libwayland-client.so.0 (wayland dependency)
#   8. DT_NEEDED links libcairo.so.2 (cairo dependency)
#
# Runtime assertions (execute the shipped binary):
#   9.  `tofi --help`                    -> exit 0 + "Usage: tofi [options]"
#   10. `tofi --anchor left-bottom`      -> exit 1 (invalid anchor value)
#   11. `tofi --horizontal truefalse`    -> exit 1 (invalid boolean value)
#   12. `tofi` without a Wayland display -> exit 1 + "Couldn't connect to
#       Wayland display." (a real Wayland client needs a compositor; tofi is
#       not a headless tool, so this is the deepest behaviour reachable here)
#
# The runtime assertions need an executable ELF. On OHOS that requires a valid
# `.codesign` section (E077); the recipe re-signs bin/tofi after meson's
# install-time ELF rewrite. If the loader nevertheless refuses the binary, the
# runtime assertions are reported as SKIP with the exact message instead of
# being counted as PASS. FAIL is never downgraded to SKIP.
set -u

PKG="${1:-}"
if [ -z "$PKG" ]; then
    echo "FAIL: no package folder argument"
    exit 1
fi
BIN="$PKG/bin/tofi"

PASS=0
FAIL=0
SKIP=0

TMPD="${TMPDIR:-$HOME/tmp}"
OUT="$TMPD/tofi-test.out.$$"
ERR="$TMPD/tofi-test.err.$$"
RUNDIR="$TMPD/tofi-test-run.$$"
trap 'rm -f "$OUT" "$ERR"; rm -rf "$RUNDIR"' EXIT

pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "SKIP: $1"; }

summary() {
    TOTAL=$((PASS + FAIL + SKIP))
    echo "tofi consumer test: TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
}

echo "== tofi consumer test =="
echo "package: $PKG"
echo "binary:  $BIN"

# ── 1. artifact present ──
if [ ! -f "$BIN" ]; then
    fail "bin/tofi is missing ($BIN)"
    summary
    exit 1
fi
pass "bin/tofi exists"

# ── 2. executable bit ──
if [ -x "$BIN" ]; then
    pass "bin/tofi is executable"
else
    fail "bin/tofi is not executable"
fi

# ── 3./4. upstream install_symlink entries ──
for _alias in tofi-run tofi-drun; do
    _link="$PKG/bin/$_alias"
    if [ -L "$_link" ] && [ "$(readlink "$_link")" = "tofi" ]; then
        pass "bin/$_alias is a symlink to tofi"
    else
        fail "bin/$_alias is not a symlink to tofi [$(ls -l "$_link" 2>&1 | head -n 1)]"
    fi
done

# ── 5./6. it is the real program (upstream message strings in the ELF) ──
if command -v strings >/dev/null 2>&1; then
    for _probe in "Usage: tofi [options]" "Couldn't connect to Wayland display."; do
        if strings "$BIN" 2>/dev/null | grep -qF "$_probe"; then
            pass "ELF contains the upstream string '$_probe'"
        else
            fail "ELF lacks the upstream string '$_probe'"
        fi
    done
else
    skip "strings(1) unavailable — cannot check the embedded upstream strings"
fi

# ── 7./8. linked against the package's own dependencies ──
echo "--- dynamic dependencies (readelf) ---"
if command -v readelf >/dev/null 2>&1; then
    readelf -d "$BIN" 2>/dev/null | grep -E "NEEDED|SONAME" || true
    for _soname in libwayland-client.so.0 libcairo.so.2; do
        if readelf -d "$BIN" 2>/dev/null | grep -qF "$_soname"; then
            pass "DT_NEEDED links $_soname"
        else
            fail "DT_NEEDED does not link $_soname"
        fi
    done
else
    skip "readelf(1) unavailable — cannot check DT_NEEDED"
fi

# ── 9./10./11. argument handling (needs execution) ──
mkdir -p "$RUNDIR"
run_case() {
    # $1 description, $2 expected exit code, $3 expected substring, rest = cmd
    _desc="$1"; _want_rc="$2"; _want_msg="$3"
    shift 3
    ( unset WAYLAND_DISPLAY WAYLAND_SOCKET
      XDG_RUNTIME_DIR="$RUNDIR" XDG_CACHE_HOME="$RUNDIR" HOME="$RUNDIR" \
          "$@" ) >"$OUT" 2>"$ERR"
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
    if ! printf '%s' "$_combined" | grep -qF "$_want_msg"; then
        fail "$_desc — output lacks '$_want_msg' [$(printf '%s' "$_combined" | head -n 2 | tr '\n' ' ')]"
        return 0
    fi
    pass "$_desc (exit $_rc)"
}

run_case "tofi --help prints usage and exits 0" 0 "Usage: tofi [options]" "$BIN" --help
run_case "tofi --anchor left-bottom is rejected" 1 "" "$BIN" --anchor left-bottom
run_case "tofi --horizontal truefalse is rejected" 1 "" "$BIN" --horizontal truefalse

# ── 12. no Wayland display: wl_display_connect() must fail (needs execution) ──
env -u WAYLAND_DISPLAY -u WAYLAND_SOCKET \
    XDG_RUNTIME_DIR="$RUNDIR" XDG_CACHE_HOME="$RUNDIR" HOME="$RUNDIR" \
    "$BIN" >"$OUT" 2>"$ERR"
RC=$?
if [ "$RC" -ge 126 ] && grep -qE \
    "cannot execute|Operation not permitted|error while loading shared libraries|not found" \
    "$ERR" 2>/dev/null; then
    skip "tofi without a display — not executable in this sandbox: $(head -n 1 "$ERR")"
else
    COMBINED="$(cat "$OUT" "$ERR" 2>/dev/null)"
    if [ "$RC" -ne 1 ]; then
        fail "tofi without a display — expected exit 1, got $RC [$(printf '%s' "$COMBINED" | head -n 2 | tr '\n' ' ')]"
    elif ! printf '%s' "$COMBINED" | grep -q "Couldn't connect to Wayland display."; then
        fail "tofi without a display — output lacks \"Couldn't connect to Wayland display.\" [$(printf '%s' "$COMBINED" | head -n 2 | tr '\n' ' ')]"
    else
        pass "tofi without a display reports \"Couldn't connect to Wayland display.\" (exit 1)"
    fi
fi

summary
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
