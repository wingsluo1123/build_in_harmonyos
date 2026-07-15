#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nrg2iso executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] nrg2iso --version"
nrg2iso --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    nrg2iso --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ nrg2iso failed both --version and --help"
        exit 1
    }
}
