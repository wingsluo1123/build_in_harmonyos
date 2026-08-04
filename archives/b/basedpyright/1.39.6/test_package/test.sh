#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for basedpyright executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] basedpyright --version"
basedpyright --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    basedpyright --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ basedpyright failed both --version and --help"
        exit 1
    }
}
