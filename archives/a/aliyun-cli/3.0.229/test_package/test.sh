#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for aliyun-cli executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] aliyun version"
aliyun version && echo "✅ version OK" || {
    echo "[test] version failed, trying help..."
    aliyun help > /dev/null 2>&1 && echo "✅ help OK" || {
        echo "❌ aliyun failed both version and help"
        exit 1
    }
}
