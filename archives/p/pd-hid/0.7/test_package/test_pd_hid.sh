#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for pd-hid 0.7.
#
# Loads the installed [hid] external with the OHOS `pd` (from the puredata
# package).  Actual HID device I/O needs real hardware (/dev/input/event*),
# but [hid] posts a deterministic banner on first instantiation:
#   "[hid] 0.7, written by Hans-Christoph Steiner <hans@eds.org>"
#   "	compiled on <date> at <time>"
#
# Env:
#   PD_BIN   path to the installed `pd` executable
#   EXT_DIR  directory holding the installed *.pd_linux externals
#   PATCH    path to test_pd_hid.pd
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
PATCH="${PATCH:?PATCH must point to test_pd_hid.pd}"

[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -f "$EXT_DIR/hid.pd_linux" ] || { echo "FAIL: hid.pd_linux missing"; exit 1; }
[ -f "$EXT_DIR/mouse.pd" ] || { echo "FAIL: mouse.pd abstraction missing"; exit 1; }

WORK="${TMPDIR:-.}/pd-hid-test.$$"
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

check "\[hid\] 0.7, written by Hans-Christoph Steiner" "hid [hid] loads and posts its version banner"
check "compiled on" "hid [hid] posts its compile timestamp"

echo "HID_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
