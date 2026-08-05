#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for czkawka_cli executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] czkawka_cli --version"
czkawka_cli --version && echo "        [ok] --version OK" || {
    echo "        [fail] --version failed, trying --help..."
    czkawka_cli --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
        echo "        [fail] czkawka_cli failed both --version and --help"
        exit 1
    }
}
