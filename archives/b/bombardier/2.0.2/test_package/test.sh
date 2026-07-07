#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bombardier
set -eu

echo "[test] bombardier --version"
bombardier --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bombardier --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bombardier failed"
        exit 1
    }
}
