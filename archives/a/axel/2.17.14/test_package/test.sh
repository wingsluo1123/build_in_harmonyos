#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for axel executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] axel --version"
axel --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    axel --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ axel failed both --version and --help"
        exit 1
    }
}
