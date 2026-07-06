#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bvi
set -eu

echo "[test] bvi --version"
bvi --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bvi --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bvi failed"
        exit 1
    }
}
