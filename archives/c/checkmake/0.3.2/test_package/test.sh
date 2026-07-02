#!/usr/bin/zsh
# test_package/test.sh — smoke test for checkmake executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] checkmake --version"
checkmake --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    checkmake --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ checkmake failed both --version and --help"
        exit 1
    }
}
