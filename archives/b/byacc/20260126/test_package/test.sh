#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for byacc
set -eu

echo "[test] byacc --version"
byacc --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    byacc --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: byacc failed"
        exit 1
    }
}
