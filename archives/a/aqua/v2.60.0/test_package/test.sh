#!/usr/bin/env bash
# test_package/test.sh — smoke test for aqua executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] aqua version"
aqua version
echo "✅ version OK"
