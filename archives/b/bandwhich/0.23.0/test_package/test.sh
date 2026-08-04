#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bandwhich executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] bandwhich --version"
bandwhich --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    bandwhich --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ bandwhich failed both --version and --help"
        exit 1
    }
}
