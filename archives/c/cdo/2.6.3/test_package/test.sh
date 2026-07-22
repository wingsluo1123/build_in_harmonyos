#!/usr/bin/env bash
# test_package/test.sh — smoke test for the cdo executable.
# Runs in conanrun env (PATH includes installed bin/).
set -eu

CDO_BIN="${CDO_BIN:-cdo}"

if [ ! -x "$CDO_BIN" ] && ! command -v "$CDO_BIN" >/dev/null 2>&1; then
    echo "FAIL: cdo binary not found: $CDO_BIN"
    exit 1
fi

echo "[test] cdo --version"
"$CDO_BIN" --version && echo "OK: --version" || {
    echo "[test] --version failed, trying --help..."
    "$CDO_BIN" --help > /dev/null 2>&1 && echo "OK: --help" || {
        echo "FAIL: cdo failed both --version and --help"
        exit 1
    }
}
