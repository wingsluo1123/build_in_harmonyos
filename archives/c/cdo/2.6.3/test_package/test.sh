#!/usr/bin/env bash
# test_package/test.sh — functional test for the cdo executable.
# Runs in conanrun env (PATH includes installed bin/).
#
# R34: Test actually exercises cdo's data-processing operators, not just
# --version/--help. We use the built-in SERVICE (srv) binary format which
# requires no external I/O library (netcdf/hdf5 are disabled in this build).
set -euo pipefail

CDO_BIN="${CDO_BIN:-cdo}"
WORKDIR="${WORKDIR:-$(mktemp -d)}"
trap 'rm -rf "$WORKDIR"' EXIT

if [ ! -x "$CDO_BIN" ] && ! command -v "$CDO_BIN" >/dev/null 2>&1; then
    echo "FAIL: cdo binary not found: $CDO_BIN"
    exit 1
fi

PASS=0
FAIL=0
ok()   { echo "OK: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# ── L1: version/help smoke ──
if "$CDO_BIN" --version >/dev/null 2>&1; then
    ok "cdo --version"
elif "$CDO_BIN" --help >/dev/null 2>&1; then
    ok "cdo --help"
else
    fail "cdo --version/--help"
fi

# ── L2: real data-processing test ──
# Build a tiny SERVICE-format field with a constant value (1.0) on a
# 2x2 grid, then verify that cdo can read it and compute a field mean
# equal to 1.0. This exercises the full read→compute→write pipeline
# using only CDO's built-in srv format — no netcdf/hdf5 needed.

# 2x2 regular grid, one field, value 1.0 everywhere
GRID="gridtype=lonlat gridsize=4 xsize=2 ysize=2 xfirst=0 xinc=1 yfirst=0 yinc=1"
INPUT="$WORKDIR/in.srv"
EXPROUT="$WORKDIR/expr.srv"
MEANOUT="$WORKDIR/mean.srv"

# Create a constant field using the expr operator
"$CDO_BIN" -f srv -expr,'field=1.0' -topo,"$GRID" "$INPUT" 2>/dev/null || {
    # Fallback: use const operator directly
    "$CDO_BIN" -f srv -const,1.0,"$GRID" "$INPUT" 2>/dev/null || {
        fail "create constant field"
        echo "SUMMARY: $PASS passed, $FAIL failed"
        exit 1
    }
}
ok "create SERVICE-format field via expr"

# Verify the field mean equals 1.0 (fldmean over the 2x2 grid)
"$CDO_BIN" -s -fldmean "$INPUT" "$MEANOUT" 2>/dev/null || {
    fail "fldmean operator"
    echo "SUMMARY: $PASS passed, $FAIL failed"
    exit 1
}
ok "fldmean statistical operator"

# Read back the mean value; should be 1.0
MEAN_VAL=$("$CDO_BIN" -s -output -fldmean "$INPUT" 2>/dev/null | head -1 || echo "")
if [ -n "$MEAN_VAL" ]; then
    # cdo -output prints one value per field; compare with tolerance
    if awk -v v="$MEAN_VAL" 'BEGIN{exit !(v > 0.999 && v < 1.001)}'; then
        ok "field mean equals 1.0 (got $MEAN_VAL)"
    else
        fail "field mean expected 1.0, got $MEAN_VAL"
    fi
else
    fail "could not read field mean value"
fi

# Format conversion: SERVICE → EXTRA (both built-in)
"$CDO_BIN" -s -f ext -copy "$INPUT" "$WORKDIR/out.ext" 2>/dev/null || {
    fail "format conversion srv→ext"
    echo "SUMMARY: $PASS passed, $FAIL failed"
    exit 1
}
ok "format conversion SERVICE → EXTRA"

if [ -f "$WORKDIR/out.ext" ] && [ -s "$WORKDIR/out.ext" ]; then
    ok "converted output file is non-empty"
else
    fail "converted output file missing or empty"
fi

echo "SUMMARY: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
