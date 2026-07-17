#!/usr/bin/env bash
# test_package/test.sh — smoke test for mkinitfs CLI tool
# Verifies that the mkinitfs binary is installed and can show help output.
set -euo pipefail

# Locate mkinitfs binary from the Conan package
MKINITFS_BIN="${1:-$(command -v mkinitfs 2>/dev/null || true)}"

if [ -z "$MKINITFS_BIN" ]; then
    # Fallback: try common Conan package layout
    for candidate in \
        "$(dirname "$0")/../../usr/sbin/mkinitfs" \
        "$(dirname "$0")/../../../usr/sbin/mkinitfs"; do
        if [ -x "$candidate" ]; then
            MKINITFS_BIN="$candidate"
            break
        fi
    done
fi

if [ -z "$MKINITFS_BIN" ]; then
    echo "❌ mkinitfs binary not found"
    exit 1
fi

echo "[test] mkinitfs binary exists: $MKINITFS_BIN"
if [ ! -s "$MKINITFS_BIN" ]; then
    echo "❌ mkinitfs binary is empty"
    exit 1
fi
echo "✅ mkinitfs binary exists and is non-empty"

echo "[test] mkinitfs -h output contains 'usage'"
# mkinitfs -h exits with code 1 on OHOS, so pipe to grep
if "$MKINITFS_BIN" -h 2>&1 | grep -q usage; then
    echo "✅ mkinitfs -h shows usage"
else
    echo "❌ mkinitfs -h did not show usage"
    exit 1
fi

echo "[test] mkinitfs smoke test: PASS"
