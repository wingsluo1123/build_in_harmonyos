#!/usr/bin/env bash
# test_package/test_xfractint.sh — headless smoke test for xfractint 20.4.10
#
# HarmonyOS PC devices ship no X display backend (knowledge E527/E463), and an
# X11 client cannot open a display in the CI environment (knowledge E530).
# A correctly built and linked xfractint must therefore:
#   1. exist as an aarch64 ELF executable,
#   2. be dynamically linked against libX11 (NEEDED entry),
#   3. run its real main() headless: with DISPLAY unset it prints
#      "Could not open display" and exits 255 (upstream exit(-1)).
# A missing shared library or relocation failure is always a FAIL.
set -uo pipefail

XFRAC_BIN="$(command -v xfractint || true)"
if [ -z "$XFRAC_BIN" ]; then
    echo "FAIL: xfractint not found on PATH (conanrun env)"
    exit 1
fi
echo "[test] xfractint binary: $XFRAC_BIN"

# --- 1: binary exists -------------------------------------------------------
if [ -f "$XFRAC_BIN" ]; then
    echo "PASS: xfractint binary exists"
else
    echo "FAIL: xfractint binary not found at $XFRAC_BIN"
    exit 1
fi

# --- 2: aarch64 ELF ---------------------------------------------------------
file_out="$(file "$XFRAC_BIN" 2>&1)"
echo "[test] file: $file_out"
if echo "$file_out" | grep -qi "ELF.*aarch64\|ELF.*arm64"; then
    echo "PASS: xfractint is an aarch64 ELF executable"
else
    echo "FAIL: xfractint is not an aarch64 ELF"
    exit 1
fi

# --- 3: linked against libX11 ----------------------------------------------
if readelf -d "$XFRAC_BIN" 2>/dev/null | grep -q "NEEDED.*libX11"; then
    echo "PASS: xfractint is dynamically linked against libX11"
else
    echo "FAIL: xfractint has no NEEDED libX11 entry"
    exit 1
fi

# --- 4: PIE -----------------------------------------------------------------
if readelf -h "$XFRAC_BIN" 2>/dev/null | grep -q "Position-Independent"; then
    echo "PASS: xfractint is a PIE executable"
else
    echo "FAIL: xfractint is not PIE"
    exit 1
fi

# --- 5: headless run must fail gracefully -----------------------------------
unset DISPLAY
if command -v timeout >/dev/null 2>&1; then
    run_out="$(timeout 30 "$XFRAC_BIN" 2>&1)"
    run_rc=$?
else
    run_out="$("$XFRAC_BIN" 2>&1)"
    run_rc=$?
fi
echo "[test] headless exit code: $run_rc"
echo "[test] headless output: $run_out"

# A loader failure is never acceptable.
if echo "$run_out" | grep -qi "error while loading\|cannot open shared object\|symbol not found"; then
    echo "FAIL: xfractint has missing shared libraries or unresolved symbols"
    echo "ldd: $(ldd "$XFRAC_BIN" 2>&1 || true)"
    exit 1
fi

if [ "$run_rc" -ne 255 ]; then
    echo "FAIL: expected exit 255 (upstream exit(-1) on missing display), got $run_rc"
    exit 1
fi
if ! echo "$run_out" | grep -q "Could not open display"; then
    echo "FAIL: expected 'Could not open display' message, got: $run_out"
    exit 1
fi
echo "PASS: xfractint ran headless and reported the expected display error"

echo ""
echo "=== All xfractint smoke tests PASSED ==="
