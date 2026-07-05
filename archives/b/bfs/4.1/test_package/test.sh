#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bfs
set -eu

echo "[test] bfs --version"
bfs --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bfs --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bfs failed"
        exit 1
    }
}
