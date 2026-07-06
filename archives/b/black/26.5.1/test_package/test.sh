#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for black
set -eu

echo "[test] black --version"
black --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    black --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: black failed"
        exit 1
    }
}
