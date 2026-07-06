#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bluez-alsa
set -eu

echo "[test] bluez-alsa --version"
bluez-alsa --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bluez-alsa --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bluez-alsa failed"
        exit 1
    }
}
