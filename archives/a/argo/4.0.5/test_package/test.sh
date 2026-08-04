#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for argo executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] argo version"
argo version && echo "✅ version OK" || {
    echo "[test] version failed, trying help..."
    argo help > /dev/null 2>&1 && echo "✅ help OK" || {
        echo "❌ argo failed both version and help"
        exit 1
    }
}
