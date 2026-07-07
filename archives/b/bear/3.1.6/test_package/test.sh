#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bear executable
set -eu

echo "[test] bear --version"
bear --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bear --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bear failed both --version and --help"
        exit 1
    }
}
