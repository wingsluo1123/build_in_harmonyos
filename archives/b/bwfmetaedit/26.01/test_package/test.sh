#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bwfmetaedit
set -eu

echo "[test] bwfmetaedit --version"
bwfmetaedit --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bwfmetaedit --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bwfmetaedit failed"
        exit 1
    }
}
