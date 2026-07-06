#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for b3sum
set -eu

echo "[test] b3sum --version"
b3sum --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    b3sum --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: b3sum failed"
        exit 1
    }
}
