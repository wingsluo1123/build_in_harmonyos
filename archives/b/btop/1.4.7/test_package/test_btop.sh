#!/data/service/hnp/bin/bash
# test_package/test_btop.sh — smoke test for btop binary
# Runs in conanrun env (PATH includes installed bin/)
set -eu

BIN="${1:-btop}"
echo "[test] btop --version"
"$BIN" --version > /dev/null 2>&1 && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    "$BIN" --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ btop failed both --version and --help"
        exit 1
    }
}
