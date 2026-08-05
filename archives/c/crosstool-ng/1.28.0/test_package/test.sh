#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for crosstool-ng executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] ct-ng --version"
ct-ng --version && echo "[ok] --version passed" || {
    echo "[step] --version failed, trying --help..."
    ct-ng --help > /dev/null 2>&1 && echo "[ok] --help passed" || {
        echo "[fail] ct-ng failed both --version and --help"
        exit 1
    }
}
