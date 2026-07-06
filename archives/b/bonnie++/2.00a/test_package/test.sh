#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bonnie++
set -eu

echo "[test] bonnie++ --version"
bonnie++ --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bonnie++ --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bonnie++ failed"
        exit 1
    }
}
