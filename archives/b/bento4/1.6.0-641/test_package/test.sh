#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bento4 executable
set -eu

echo "[test] bento4 --version"
bento4 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bento4 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bento4 failed both --version and --help"
        exit 1
    }
}
