#!/usr/bin/zsh
# test_apko.sh — Smoke test for apko binary
# R34: This script exercises the actual apko binary from the conan package.
# CI L0c requires a .sh/.py/.c source file in test_package/.
set -euo pipefail

APKO_BIN="${1:-apko}"

# Run apko version and verify output contains version string
OUTPUT=$("$APKO_BIN" version 2>&1) || {
    echo "[fail] apko version exited with error" >&2
    exit 1
}

echo "$OUTPUT" | grep -q "1.2.17" || {
    echo "[fail] apko version output does not contain 1.2.17" >&2
    exit 1
}

echo "[ok] apko version contains 1.2.17"
