#!/usr/bin/env bash
# R34: real smoke test for apitrace 14.0 — exercises the packaged artifact.
# apitrace is a command-line tool for tracing graphics API calls.
# We verify the apitrace binary exists, is executable, and responds to commands.
set -euo pipefail

PKG_DIR="${1:?usage: test_apitrace.sh <package root dir>}"

FAIL=0

# Check apitrace binary
APITRACE="$PKG_DIR/bin/apitrace"
if [ ! -x "$APITRACE" ]; then
    echo "FAIL: apitrace binary missing or not executable in $PKG_DIR/bin"
    FAIL=1
else
    # Run apitrace without args — it prints usage and exits non-zero (expected)
    OUTPUT=$("$APITRACE" 2>&1) || true  # apitrace exits 1 on no args; ignore
    if ! echo "$OUTPUT" | grep -qi "command"; then
        echo "FAIL: apitrace did not print usage (expected 'command' in output)"
        FAIL=1
    fi
fi

# Check gltrim binary
GLTRIM="$PKG_DIR/bin/gltrim"
if [ ! -x "$GLTRIM" ]; then
    echo "FAIL: gltrim binary missing or not executable in $PKG_DIR/bin"
    FAIL=1
fi

# Check egltrace.so wrapper
EGLTRACE="$PKG_DIR/lib/apitrace/wrappers/egltrace.so"
if [ ! -f "$EGLTRACE" ]; then
    echo "FAIL: egltrace.so wrapper missing in $PKG_DIR/lib/apitrace/wrappers"
    FAIL=1
fi

# Check Python scripts present
SCRIPTS_DIR="$PKG_DIR/lib/apitrace/scripts"
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "FAIL: scripts directory missing in $PKG_DIR/lib/apitrace/scripts"
    FAIL=1
else
    for script in convert.py tracediff.py snapdiff.py; do
        if [ ! -f "$SCRIPTS_DIR/$script" ]; then
            echo "FAIL: $script missing in scripts directory"
            FAIL=1
        fi
    done
fi

if [ "$FAIL" -eq 0 ]; then
    echo "apitrace smoke test: OK"
fi
exit "$FAIL"
