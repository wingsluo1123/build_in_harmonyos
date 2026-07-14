#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dante sockd
# Runs in conanrun env (PATH includes installed sbin/)
set -euo pipefail

echo "[step] sockd version check"
sockd -v && echo "        [ok] sockd -v passed" || {
    echo "        [fail] sockd -v failed, trying -h..."
    sockd -h > /dev/null 2>&1 && echo "        [ok] sockd -h passed" || {
        echo "        [fail] sockd failed both -v and -h"
        exit 1
    }
}
