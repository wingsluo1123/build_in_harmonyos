#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for basedpyright
set -eu

echo "[test] basedpyright --version"
basedpyright --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    basedpyright --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: basedpyright failed"
        exit 1
    }
}
