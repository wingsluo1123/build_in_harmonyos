#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for byobu
set -eu

echo "[test] byobu --version"
byobu --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    byobu --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: byobu failed"
        exit 1
    }
}
