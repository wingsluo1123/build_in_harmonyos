#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-boids 1.1.1.
#
# Loads the installed boids externals with the OHOS `pd` (from the
# puredata package) and checks the deterministic `dump` parameter
# report of both classes.  The default number of neighbours is 2.
#
#   [boids2d 4 0] + dump -> "neighbors 2"
#   [boids3d 4 0] + dump -> "neighbors 2"
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_boids.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_boids.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/boids2d.pd_linux" ] || { echo "FAIL: boids2d.pd_linux missing"; exit 1; }
[ -f "$EXT_DIR/boids3d.pd_linux" ] || { echo "FAIL: boids3d.pd_linux missing"; exit 1; }

WORK="${TMPDIR:-.}/pd-boids-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

LOG="$WORK/pd.log"
if command -v timeout >/dev/null 2>&1; then
    timeout 20 "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
else
    "$PD_BIN" -nogui -nosound -path "$EXT_DIR" -open "$PATCH" > "$LOG" 2>&1 || true
fi

echo "--- pd output ---"
cat "$LOG"
echo "--- end pd output ---"

fails=0
check() {
    if grep -q "$1" "$LOG"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2 (expected '$1')"
        fails=$((fails + 1))
    fi
}

check "BOIDS2D_DUMP: neighbors 2" "boids [boids2d] dump reports neighbors 2"
check "BOIDS3D_DUMP: neighbors 2" "boids [boids3d] dump reports neighbors 2"

echo "BOIDS_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
