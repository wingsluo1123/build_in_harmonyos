#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for brunsli executable
set -eu

echo "[test] brunsli --version"
brunsli --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    brunsli --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: brunsli failed both --version and --help"
        exit 1
    }
}
