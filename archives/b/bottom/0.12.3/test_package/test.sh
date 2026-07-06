#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bottom
set -eu

echo "[test] bottom --version"
bottom --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bottom --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bottom failed"
        exit 1
    }
}
