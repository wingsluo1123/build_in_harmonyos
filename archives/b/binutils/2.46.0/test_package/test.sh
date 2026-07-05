#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for binutils
set -eu

echo "[test] binutils --version"
binutils --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    binutils --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: binutils failed"
        exit 1
    }
}
