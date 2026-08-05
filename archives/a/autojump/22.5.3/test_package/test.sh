#!/bin/bash
# test.sh — autojump smoke test
# Runs autojump --version to verify the installed binary works correctly.
set -euo pipefail

AUTOJUMP_BIN="${AUTOJUMP_PATH:-$(find "${PACKAGE_DIR:-/}" -name autojump -type f 2>/dev/null | head -1)}"

if [ -z "$AUTOJUMP_BIN" ]; then
    echo "        [fail] autojump binary not found"
    exit 1
fi

VERSION_OUTPUT=$(python3 "$AUTOJUMP_BIN" --version 2>&1)
echo "$VERSION_OUTPUT"

if echo "$VERSION_OUTPUT" | grep -q "22.5.3"; then
    echo "        [ok] autojump --version test passed"
else
    echo "        [fail] autojump --version output does not contain 22.5.3"
    exit 1
fi
