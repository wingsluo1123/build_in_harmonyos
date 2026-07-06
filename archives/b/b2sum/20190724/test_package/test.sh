#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for b2sum
set -eu

echo "[test] b2sum --version"
b2sum --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    b2sum --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: b2sum failed"
        exit 1
    }
}
