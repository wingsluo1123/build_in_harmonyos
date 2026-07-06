#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bcrypt
set -eu

echo "[test] bcrypt --version"
bcrypt --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bcrypt --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bcrypt failed"
        exit 1
    }
}
