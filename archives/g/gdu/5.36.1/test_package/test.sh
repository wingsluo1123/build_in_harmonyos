#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gdu executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] gdu --version"
gdu --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    gdu --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ gdu failed both --version and --help"
        exit 1
    }
}
