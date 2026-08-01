#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for docuum binary
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

BIN="${1:-docuum}"
echo "[test] docuum --help"
"$BIN" --help > /dev/null 2>&1 && echo "✅ --help OK" || {
    echo "[test] --help failed, trying --version..."
    "$BIN" --version > /dev/null 2>&1 && echo "✅ --version OK" || {
        echo "❌ docuum failed both --help and --version"
        exit 1
    }
}
