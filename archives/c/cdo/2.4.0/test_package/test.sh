#!/usr/bin/env bash
# test_package/test.sh — smoke test for the cdo executable.
# Runs in conanrun env (PATH includes installed bin/).
set -eu

echo "[test] cdo --version"
cdo --version && echo "OK: --version" || {
    echo "[test] --version failed, trying --help..."
    cdo --help > /dev/null 2>&1 && echo "OK: --help" || {
        echo "FAIL: cdo failed both --version and --help"
        exit 1
    }
}
