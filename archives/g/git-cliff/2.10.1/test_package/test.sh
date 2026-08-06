#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for git-cliff executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] git-cliff --version"
git-cliff --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    git-cliff --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ git-cliff failed both --version and --help"
        exit 1
    }
}
