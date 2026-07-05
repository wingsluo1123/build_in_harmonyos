#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bibutils
set -eu

echo "[test] bibutils --version"
bibutils --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bibutils --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bibutils failed"
        exit 1
    }
}
