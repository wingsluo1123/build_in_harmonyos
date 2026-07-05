#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bzip2 executable
set -eu

echo "[test] bzip2 --version"
bzip2 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bzip2 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bzip2 failed both --version and --help"
        exit 1
    }
}
