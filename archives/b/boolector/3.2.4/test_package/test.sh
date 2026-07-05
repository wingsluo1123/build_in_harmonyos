#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for boolector
set -eu

echo "[test] boolector --version"
boolector --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    boolector --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: boolector failed"
        exit 1
    }
}
