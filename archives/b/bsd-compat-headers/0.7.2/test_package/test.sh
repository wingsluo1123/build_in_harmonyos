#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bsd-compat-headers
set -eu

echo "[test] bsd-compat-headers --version"
bsd-compat-headers --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bsd-compat-headers --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bsd-compat-headers failed"
        exit 1
    }
}
