#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bbe
set -eu

echo "[test] bbe --version"
bbe --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bbe --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bbe failed"
        exit 1
    }
}
