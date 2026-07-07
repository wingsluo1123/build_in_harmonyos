#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bzip3
set -eu

echo "[test] bzip3 --version"
bzip3 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bzip3 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bzip3 failed"
        exit 1
    }
}
