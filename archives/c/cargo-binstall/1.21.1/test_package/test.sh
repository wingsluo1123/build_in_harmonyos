#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cargo-binstall precompiled binaries
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binaries.
set -eu

echo "[test] cargo-binstall -V"
VERSION=$(cargo-binstall -V 2>&1)
echo "  Output: $VERSION"
echo "$VERSION" | grep -q "1.21.1"
echo "OK: cargo-binstall -V returns version 1.21.1"

echo "[test] detect-targets"
TARGETS=$(detect-targets 2>&1)
echo "  Output: $TARGETS"
echo "$TARGETS" | grep -q "aarch64"
echo "OK: detect-targets reports aarch64 target"

echo "[test] detect-wasi"
WASI=$(detect-wasi 2>&1) || true
echo "  Output: $WASI"
if [ -n "$WASI" ]; then
    echo "OK: detect-wasi produces output"
else
    echo "FAIL: detect-wasi produced no output"
    exit 1
fi

echo "[test] cargo-binstall --help (partial)"
HELP=$(cargo-binstall --help 2>&1 | head -5) || true
echo "  Output: $HELP"
# Use case statement for portability (grep -E may vary on HarmonyOS)
case "$HELP" in
    *Install*|*cargo*|*binstall*|*Rust*)
        echo "OK: cargo-binstall --help shows usage info"
        ;;
    *)
        echo "FAIL: cargo-binstall --help unexpected output"
        exit 1
        ;;
esac

echo ""
echo "=== All tests passed ==="
