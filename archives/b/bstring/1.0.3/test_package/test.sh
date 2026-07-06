#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bstring executable
set -eu

echo "[test] bstring --version"
bstring --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bstring --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bstring failed both --version and --help"
        exit 1
    }
}
