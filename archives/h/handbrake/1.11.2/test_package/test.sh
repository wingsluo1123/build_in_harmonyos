#!/bin/sh
# test_package/test.sh — real smoke test for HandBrakeCLI
# Runs in the conanrun env (PATH includes the installed bin/).
set -eu

CLI="HandBrakeCLI"

if ! command -v "$CLI" >/dev/null 2>&1; then
    echo "[test] FAIL: $CLI not found in PATH"
    exit 1
fi

echo "[test] $CLI --version"
set +e
"$CLI" --version >/dev/null 2>&1
ret=$?
set -e
if [ "$ret" -ne 0 ]; then
    echo "[test] FAIL: $CLI --version exited with $ret"
    exit 1
fi
echo "[test] OK: $CLI --version returned 0"

echo "[test] $CLI --help (sanity)"
set +e
"$CLI" --help >/dev/null 2>&1
ret=$?
set -e
if [ "$ret" -ne 0 ]; then
    echo "[test] FAIL: $CLI --help exited with $ret"
    exit 1
fi
echo "[test] OK: $CLI --help ran"
exit 0
