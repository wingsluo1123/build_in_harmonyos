#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for blosc executable
set -eu

echo "[test] blosc --version"
blosc --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    blosc --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: blosc failed both --version and --help"
        exit 1
    }
}
