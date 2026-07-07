#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bitrise
set -eu

echo "[test] bitrise --version"
bitrise --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bitrise --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bitrise failed"
        exit 1
    }
}
