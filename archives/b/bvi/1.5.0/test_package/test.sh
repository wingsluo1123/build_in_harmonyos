#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bvi executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] bvi --version"
bvi --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    bvi --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ bvi failed both --version and --help"
        exit 1
    }
}
