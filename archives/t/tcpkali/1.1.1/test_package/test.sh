#!/bin/sh
# test_package/test.sh — smoke test for tcpkali executable
set -eu

echo "[test] tcpkali --version"
tcpkali --version && echo "[ok] --version output verified" || {
    echo "[fail] tcpkali --version failed"
    exit 1
}
