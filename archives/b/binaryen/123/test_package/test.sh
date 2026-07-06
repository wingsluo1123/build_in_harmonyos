#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for binaryen executable
set -eu

echo "[test] binaryen --version"
binaryen --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    binaryen --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: binaryen failed both --version and --help"
        exit 1
    }
}
