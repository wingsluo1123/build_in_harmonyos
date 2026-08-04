#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bandwhich executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] bandwhich --version"
bandwhich --version && echo "[ok] --version passed" || {
    echo "[step] --version failed, trying --help..."
    bandwhich --help > /dev/null 2>&1 && echo "[ok] --help passed" || {
        echo "[fail] bandwhich failed both --version and --help"
        exit 1
    }
}
