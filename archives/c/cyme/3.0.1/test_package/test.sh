#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cyme executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] cyme --version"
cyme --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    cyme --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ cyme failed both --version and --help"
        exit 1
    }
}
