#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bpm-tools
set -eu

echo "[test] bpm-tools --version"
bpm-tools --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bpm-tools --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bpm-tools failed"
        exit 1
    }
}
