#!/bin/bash
# test.sh — bottom 0.12.3 test_package
# Runs btm --version and verifies the output.

set -euo pipefail

# VirtualRunEnv sets PATH to include the package's bin/ directory
BTM="$(command -v btm 2>/dev/null || true)"  # may not be in PATH yet
if [ -z "$BTM" ]; then
    # Fallback: search common locations
    for dir in $(echo "$PATH" | tr ':' ' '); do
        if [ -x "$dir/btm" ]; then
            BTM="$dir/btm"
            break
        fi
    done
fi

if [ -z "$BTM" ]; then
    echo "FAIL: btm binary not found in PATH"
    exit 1
fi

echo "Found btm at: $BTM"
OUTPUT="$("$BTM" --version 2>&1)"
echo "btm --version output: $OUTPUT"

case "$OUTPUT" in
    *"bottom 0.12.3"*)
        echo "PASS: btm --version reports correct version"
        exit 0
        ;;
    *)
        echo "FAIL: btm --version output does not match expected version"
        exit 1
        ;;
esac
