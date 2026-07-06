#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for blake3 executable
set -eu

echo "[test] blake3 --version"
blake3 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    blake3 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: blake3 failed both --version and --help"
        exit 1
    }
}
