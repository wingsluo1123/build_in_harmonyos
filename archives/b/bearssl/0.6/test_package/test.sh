#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bearssl executable
set -eu

echo "[test] bearssl --version"
bearssl --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bearssl --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bearssl failed both --version and --help"
        exit 1
    }
}
