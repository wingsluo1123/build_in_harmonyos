#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for basisu executable
set -eu

echo "[test] basisu --version"
basisu --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    basisu --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: basisu failed both --version and --help"
        exit 1
    }
}
