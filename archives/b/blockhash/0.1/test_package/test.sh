#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for blockhash
set -eu

echo "[test] blockhash --version"
blockhash --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    blockhash --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: blockhash failed"
        exit 1
    }
}
