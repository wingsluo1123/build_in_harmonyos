#!/bin/sh
# test_package/test.sh — smoke test for apko executable
# Runs in conanrun env (PATH includes installed bin/).
set -eu

echo "[test] apko version"
if apko version; then
    echo "[ok] version"
else
    echo "[test] version failed (exit $?), trying --help..."
    if apko --help > /dev/null 2>&1; then
        echo "[ok] --help"
    else
        echo "[fail] apko failed both version and --help"
        exit 1
    fi
fi
