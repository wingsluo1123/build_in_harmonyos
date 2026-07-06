#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for base64
set -eu

echo "[test] base64 --version"
base64 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    base64 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: base64 failed"
        exit 1
    }
}
