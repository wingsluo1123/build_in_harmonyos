#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for redsocks executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] redsocks -v"
if redsocks -v 2>&1; then
    echo "        [ok] redsocks -v passed"
else
    echo "[step] -v failed, trying -h..."
    if redsocks -h > /dev/null 2>&1; then
        echo "        [ok] redsocks -h passed"
    else
        echo "        [fail] redsocks failed both -v and -h"
        exit 1
    fi
fi
