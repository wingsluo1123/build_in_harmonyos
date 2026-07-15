#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for colordiff executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] colordiff --version"
colordiff --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    colordiff --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ colordiff failed both --version and --help"
        exit 1
    }
}
