#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bc
set -eu

echo "[test] bc --version"
bc --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bc --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bc failed"
        exit 1
    }
}
