#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for babl executable
set -eu

echo "[test] babl --version"
babl --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    babl --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: babl failed both --version and --help"
        exit 1
    }
}
