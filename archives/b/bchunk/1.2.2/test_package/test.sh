#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bchunk
set -eu

echo "[test] bchunk --version"
bchunk --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bchunk --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bchunk failed"
        exit 1
    }
}
