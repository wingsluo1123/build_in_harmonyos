#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bkcrack
set -eu

echo "[test] bkcrack --version"
bkcrack --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bkcrack --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bkcrack failed"
        exit 1
    }
}
