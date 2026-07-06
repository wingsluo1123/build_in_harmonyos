#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bcal
set -eu

echo "[test] bcal --version"
bcal --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bcal --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bcal failed"
        exit 1
    }
}
