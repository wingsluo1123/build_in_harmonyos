#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for borgbackup executable
set -eu

echo "[test] borgbackup --version"
borgbackup --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    borgbackup --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: borgbackup failed both --version and --help"
        exit 1
    }
}
