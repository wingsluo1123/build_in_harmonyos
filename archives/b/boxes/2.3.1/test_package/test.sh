#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for boxes
set -eu

echo "[test] boxes --version"
boxes --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    boxes --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: boxes failed"
        exit 1
    }
}
