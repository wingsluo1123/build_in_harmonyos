#!/usr/bin/env bash
#--------------------------------------------------------------------
# Consumer test for xtrs 4.9d.
#
# Upstream has no test suite. This drives the three headless CLI tools with
# deterministic inputs and checks the emulator binary loads:
#   hex2cmd  Intel-HEX -> CMD      (upstream fakerom.hex -> 154-byte .cmd)
#   cmddump  dump a CMD file       (prints load range + transfer address)
#   mkdisk   create a blank disk   (Model III image is 8704 bytes)
#   xtrs     X11 emulator; with no DISPLAY it must load and report it
#
# Env:
#   BIN_DIR      directory with the installed xtrs/mkdisk/hex2cmd/cmddump
#   FIXTURE_DIR  directory holding fakerom.hex
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -euo pipefail

BIN_DIR="${BIN_DIR:?BIN_DIR must point to the installed bin}"
FIXTURE_DIR="${FIXTURE_DIR:?FIXTURE_DIR must point to the fixtures}"
HEX="$FIXTURE_DIR/fakerom.hex"

[ -x "$BIN_DIR/hex2cmd" ] || { echo "FAIL: hex2cmd missing"; exit 1; }
[ -f "$HEX" ] || { echo "FAIL: fixture missing: $HEX"; exit 1; }

# Make the xtrs check deterministic regardless of the caller's environment.
unset DISPLAY

BASE="${TMPDIR:-$PWD}"
WORK="$(cd "$BASE" && pwd)/xtrs-test.$$"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

fails=0
check() {
    if [ "$1" = "1" ]; then
        echo "PASS: $2"
    else
        echo "FAIL: $2"
        fails=$((fails + 1))
    fi
}

# 1) hex2cmd: upstream fakerom.hex -> TRS-80 CMD (154 bytes)
"$BIN_DIR/hex2cmd" "$HEX" > rom.cmd
sz=$(wc -c < rom.cmd | tr -d ' ')
check "$([ "$sz" -eq 154 ] && echo 1 || echo 0)" "hex2cmd fakerom.hex -> 154-byte .cmd (got $sz)"

# 2/3) cmddump: prints the loaded address range and the transfer address
"$BIN_DIR/cmddump" rom.cmd > dump.txt 2>&1
grep -q "loaded 0x" dump.txt && check 1 "cmddump prints loaded address range" || check 0 "cmddump prints loaded address range"
grep -q "transfer address = 0x" dump.txt && check 1 "cmddump prints transfer address" || check 0 "cmddump prints transfer address"

# 4) mkdisk: Model III single-density image is 8704 bytes
"$BIN_DIR/mkdisk" -3 disk3.dsk
sz3=$(wc -c < disk3.dsk | tr -d ' ')
check "$([ "$sz3" -eq 8704 ] && echo 1 || echo 0)" "mkdisk -3 creates an 8704-byte image (got $sz3)"

# 5) xtrs: loads the X11 stack and reaches display init (no DISPLAY here)
if command -v timeout >/dev/null 2>&1; then
    timeout 8 "$BIN_DIR/xtrs" > xtrs.log 2>&1 || true
else
    "$BIN_DIR/xtrs" > xtrs.log 2>&1 || true
fi
grep -q "Unable to open display" xtrs.log && check 1 "xtrs loads libX11 and reports missing display" || check 0 "xtrs loads libX11 and reports missing display"

echo "XTRS_CHECK_SUMMARY fails=$fails"
[ "$fails" -eq 0 ]
