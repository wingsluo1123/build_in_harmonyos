#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bgrep
set -eu

echo "[test] bgrep --version"
bgrep --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bgrep --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bgrep failed"
        exit 1
    }
}
