#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for blend2d executable
set -eu

echo "[test] blend2d --version"
blend2d --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    blend2d --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: blend2d failed both --version and --help"
        exit 1
    }
}
