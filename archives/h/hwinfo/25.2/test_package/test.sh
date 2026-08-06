#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for hwinfo executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] hwinfo --version"
hwinfo --version && echo "        [ok] --version" || {
    echo "        [fail] --version failed, trying --help..."
    hwinfo --help > /dev/null 2>&1 && echo "        [ok] --help" || {
        echo "        [fail] hwinfo failed both --version and --help"
        exit 1
    }
}
