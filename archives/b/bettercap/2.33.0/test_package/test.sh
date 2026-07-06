#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bettercap
set -eu

echo "[test] bettercap --version"
bettercap --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bettercap --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bettercap failed"
        exit 1
    }
}
