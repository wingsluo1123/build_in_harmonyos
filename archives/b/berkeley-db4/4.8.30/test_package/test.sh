#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for berkeley-db4 executable
set -eu

echo "[test] berkeley-db4 --version"
berkeley-db4 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    berkeley-db4 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: berkeley-db4 failed both --version and --help"
        exit 1
    }
}
