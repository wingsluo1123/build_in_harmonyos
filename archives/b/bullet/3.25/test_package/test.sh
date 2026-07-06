#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bullet executable
set -eu

echo "[test] bullet --version"
bullet --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bullet --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bullet failed both --version and --help"
        exit 1
    }
}
