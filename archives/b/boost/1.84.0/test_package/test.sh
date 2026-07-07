#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for boost executable
set -eu

echo "[test] boost --version"
boost --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    boost --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: boost failed both --version and --help"
        exit 1
    }
}
