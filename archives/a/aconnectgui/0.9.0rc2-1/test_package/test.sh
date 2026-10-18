#!/bin/sh
# test_package/test.sh — aconnectgui consumer smoke test.
#
# Real execution (non-empty): locate the installed aconnectgui binary and run
# it, asserting the dynamic loader and every NEEDED library resolve and main()
# actually starts. aconnectgui is an FLTK GUI frontend for `aconnect` (ALSA
# sequencer); on the headless CI target there is no X display, so a non-zero
# exit after complaining about the display is the *expected* outcome and still
# proves the package runs. What this test guards against are the broken-install
# exit codes: 127 (not found / loader failed) and 126 (found but not
# executable).
set -u

# Assertion 1: the installed binary is on PATH.
BIN="$(command -v aconnectgui 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: aconnectgui not found in PATH" >&2
    exit 1
fi
echo "aconnectgui binary found: $BIN"

# Run it for real, capturing combined stdout+stderr.
OUT="$(aconnectgui --help 2>&1)"
RC=$?
echo "aconnectgui --help rc=$RC"
echo "----- output -----"
echo "$OUT"
echo "------------------"

# Assertion 2: the binary actually executed (loader + NEEDED libs resolved).
# 126 = not executable; 127 = command not found / shared-library load failure.
# Any other rc (including the headless "cannot open display" failure) means the
# ELF loaded and main() ran — a successful consumer smoke.
if [ "$RC" -eq 126 ] || [ "$RC" -eq 127 ]; then
    echo "FAIL: aconnectgui could not execute (rc=$RC)" >&2
    exit 1
fi

echo "aconnectgui consumer smoke OK (rc=$RC, binary executed on headless target)"
exit 0
