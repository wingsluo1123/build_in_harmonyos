#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for git-lfs executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] git-lfs version"
git-lfs version && echo "✅ version OK" || {
    echo "[test] version failed, trying --help..."
    git-lfs --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ git-lfs failed both version and --help"
        exit 1
    }
}
