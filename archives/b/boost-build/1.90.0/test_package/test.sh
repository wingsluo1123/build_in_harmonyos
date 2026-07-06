#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for boost-build executable
set -eu

echo "[test] boost-build --version"
boost-build --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    boost-build --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: boost-build failed both --version and --help"
        exit 1
    }
}
