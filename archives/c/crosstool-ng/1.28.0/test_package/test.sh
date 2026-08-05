#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for crosstool-ng executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] ct-ng --version"
ct-ng --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    ct-ng --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ ct-ng failed both --version and --help"
        exit 1
    }
}
