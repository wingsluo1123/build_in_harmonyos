#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for btrfs-progs
set -eu

echo "[test] btrfs-progs --version"
btrfs-progs --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    btrfs-progs --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: btrfs-progs failed"
        exit 1
    }
}
