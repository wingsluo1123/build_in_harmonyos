#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bsdiff executable
set -eu

echo "[test] bsdiff --version"
bsdiff --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bsdiff --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bsdiff failed both --version and --help"
        exit 1
    }
}
