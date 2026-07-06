#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bash
set -eu

echo "[test] bash --version"
bash --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bash --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bash failed"
        exit 1
    }
}
