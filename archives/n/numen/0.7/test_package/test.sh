#!/bin/sh
# test_package/test.sh — smoke test for numen executable
# Runs `numen --version` to verify the binary is functional.
# Note: Full numen operation requires a microphone + vosk model, which is
# beyond CI scope, so we only smoke-test the --version flag.
set -eu

NUMEN_BIN="${1:-numen}"

echo "[test] numen --version"
if ! command -v "$NUMEN_BIN" >/dev/null 2>&1; then
    # Fall back to PATH-resolved numen (conanrun env should put it on PATH)
    NUMEN_BIN="numen"
fi

# Verify binary exists and is executable
if ! command -v "$NUMEN_BIN" >/dev/null 2>&1; then
    echo "❌ numen binary not found on PATH"
    exit 1
fi

# numen --version prints the version string set via -ldflags
output=$("$NUMEN_BIN" --version) || {
    echo "❌ numen --version exited non-zero"
    exit 1
}

echo "Output: $output"
case "$output" in
    *[0-9]*)
        echo "✅ numen --version returned a version string"
        ;;
    *)
        echo "❌ numen --version output missing version number"
        exit 1
        ;;
esac

# Also verify numenc companion script is on PATH
if ! command -v numenc >/dev/null 2>&1; then
    echo "⚠ numenc companion script not found on PATH (may be optional)"
fi

echo "[test] numen smoke test passed"
