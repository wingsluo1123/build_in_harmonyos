#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-markex 0.85.
#
# Loads the installed markex externals with the OHOS `pd` (from the
# puredata package) and drives three deterministic classes:
#   [rgb2hsv] on "1 0 0"    -> "0 1 1"
#   [hsv2rgb] on "0 1 1"    -> "1 0 0"
#   [strcat foo] on symbol bar -> symbol "foobar"
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_markex.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_markex.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/rgb2hsv.pd_linux" ] || { echo "FAIL: rgb2hsv.pd_linux missing"; exit 1; }

WORK="${TMPDIR:-.}/pd-markex-test.$$"
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

check "MARKEX_RGB2HSV: 0 1 1" "markex [rgb2hsv] 1 0 0 -> 0 1 1"
check "MARKEX_HSV2RGB: 1 0 0" "markex [hsv2rgb] 0 1 1 -> 1 0 0"
check "MARKEX_STRCAT: symbol foobar" "markex [strcat foo] symbol bar -> foobar"

echo "MARKEX_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
