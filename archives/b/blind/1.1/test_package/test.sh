#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for blind
set -eu

echo "[test] blind --version"
blind --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    blind --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: blind failed"
        exit 1
    }
}
