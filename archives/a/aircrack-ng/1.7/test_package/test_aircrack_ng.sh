#!/usr/bin/env bash
# R34: smoke test for aircrack-ng 1.7 — exercises the packaged binaries.
# Verifies presence, executable bit, and version output.
set -euo pipefail

BIN_DIR="${1:?usage: test_aircrack_ng.sh <package bin dir>}"

FAIL=0

# Check all expected binaries exist and are executable
for f in aircrack-ng kstats makeivs-ng; do
    if [ ! -x "$BIN_DIR/$f" ]; then
        echo "FAIL: $f missing or not executable in $BIN_DIR"
        FAIL=1
    fi
done

# Run aircrack-ng with no args — should print version "Aircrack-ng 1.7"
AIRCRACK="$BIN_DIR/aircrack-ng"
if [ -x "$AIRCRACK" ]; then
    OUTPUT=$("$AIRCRACK" 2>&1 || true)
    if ! echo "$OUTPUT" | grep -q "Aircrack-ng 1.7"; then
        echo "FAIL: aircrack-ng version mismatch or no output"
        FAIL=1
    fi
fi

# Run makeivs-ng with no args — should print version
MAKEIVS="$BIN_DIR/makeivs-ng"
if [ -x "$MAKEIVS" ]; then
    OUTPUT=$("$MAKEIVS" 2>&1 || true)
    if ! echo "$OUTPUT" | grep -q "makeivs-ng 1.7"; then
        echo "FAIL: makeivs-ng version mismatch or no output"
        FAIL=1
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "aircrack-ng smoke test: OK"
fi
exit "$FAIL"
