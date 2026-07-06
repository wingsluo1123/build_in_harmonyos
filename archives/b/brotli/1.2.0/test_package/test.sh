#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for brotli executable
set -eu

echo "[test] brotli --version"
brotli --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    brotli --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: brotli failed both --version and --help"
        exit 1
    }
}
