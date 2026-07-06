#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bossa
set -eu

echo "[test] bossa --version"
bossa --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bossa --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bossa failed"
        exit 1
    }
}
