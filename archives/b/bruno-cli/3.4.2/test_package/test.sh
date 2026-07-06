#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bruno-cli
set -eu

echo "[test] bruno-cli --version"
bruno-cli --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bruno-cli --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bruno-cli failed"
        exit 1
    }
}
