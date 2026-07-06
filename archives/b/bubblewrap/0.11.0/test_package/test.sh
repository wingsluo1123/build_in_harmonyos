#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bubblewrap
set -eu

echo "[test] bubblewrap --version"
bubblewrap --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bubblewrap --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bubblewrap failed"
        exit 1
    }
}
