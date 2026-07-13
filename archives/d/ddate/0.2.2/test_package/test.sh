#!/bin/sh
# test_package/test.sh — smoke test for ddate executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] ddate output"
ddate && echo "✅ ddate runs OK" || {
    echo "❌ ddate failed to run"
    exit 1
}
