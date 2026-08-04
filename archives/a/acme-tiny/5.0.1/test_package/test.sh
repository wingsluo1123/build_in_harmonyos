#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for acme-tiny executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] acme-tiny --help"
acme-tiny --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
    echo "        [fail] acme-tiny --help failed"
    exit 1
}
