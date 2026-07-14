#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dante sockd
# Runs in conanrun env (PATH includes installed sbin/)
set -eu

echo "[test] sockd -v"
sockd -v && echo "✅ sockd -v OK" || {
    echo "[test] -v failed, trying -h..."
    sockd -h > /dev/null 2>&1 && echo "✅ sockd -h OK" || {
        echo "❌ sockd failed both -v and -h"
        exit 1
    }
}
