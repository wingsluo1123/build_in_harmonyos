#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bmd-tools
set -eu

echo "[test] bmd-tools --version"
bmd-tools --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bmd-tools --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bmd-tools failed"
        exit 1
    }
}
