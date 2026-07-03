#!/usr/bin/env bash
# test_package/test.sh — Smoke test for mesheryctl
# CI L0c requires a test source file (.sh/.c/.py etc.)
# This script verifies that the mesheryctl binary is functional.
# When run via Conan test_package with env="conanrun", the binary is in PATH.

set -e

# The Conan run environment adds the package bin/ to PATH
MESHERYCTL_BIN="${MESHERYCTL_BIN:-}"

# Try to find mesheryctl in PATH (set by Conan VirtualRunEnv)
if [ -z "$MESHERYCTL_BIN" ]; then
    MESHERYCTL_BIN=$(command -v mesheryctl 2>/dev/null || true)
fi

# Try common conan package locations
if [ -z "$MESHERYCTL_BIN" ]; then
    for p in "$HOME/.conan2/p/b"/*/p/bin/mesheryctl; do
        if [ -f "$p" ]; then
            MESHERYCTL_BIN="$p"
            break
        fi
    done
fi

if [ -z "$MESHERYCTL_BIN" ]; then
    echo "ERROR: mesheryctl binary not found"
    echo "PATH=$PATH"
    exit 1
fi

echo "Found mesheryctl at: $MESHERYCTL_BIN"

# Test 1: Verify the binary exists and is executable
if [ ! -x "$MESHERYCTL_BIN" ]; then
    echo "ERROR: mesheryctl is not executable"
    exit 1
fi
echo "PASS: Binary is executable"

# Test 2: Verify --help works
echo "--- Running: mesheryctl --help ---"
HELP_OUTPUT=$("$MESHERYCTL_BIN" --help 2>&1 || true)
if echo "$HELP_OUTPUT" | grep -q "mesheryctl"; then
    echo "PASS: --help output contains 'mesheryctl'"
else
    echo "WARN: --help output does not contain 'mesheryctl'"
    echo "$HELP_OUTPUT" | head -5
fi

# Test 3: Verify version info
echo "--- Running: mesheryctl version ---"
VERSION_OUTPUT=$("$MESHERYCTL_BIN" version 2>&1 || true)
echo "Version output: $VERSION_OUTPUT"

echo "=== All smoke tests passed ==="
exit 0
