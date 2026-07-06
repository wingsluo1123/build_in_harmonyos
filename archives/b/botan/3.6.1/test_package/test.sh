#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for botan executable
set -eu

echo "[test] botan --version"
botan --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    botan --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: botan failed both --version and --help"
        exit 1
    }
}
