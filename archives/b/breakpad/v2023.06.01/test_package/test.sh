#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for breakpad
set -eu

echo "[test] breakpad --version"
breakpad --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    breakpad --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: breakpad failed"
        exit 1
    }
}
