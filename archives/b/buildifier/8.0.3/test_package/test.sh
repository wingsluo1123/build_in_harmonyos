#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for buildifier
set -eu

echo "[test] buildifier --version"
buildifier --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    buildifier --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: buildifier failed"
        exit 1
    }
}
