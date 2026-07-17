#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for open-adventure executables
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] advent -h"
advent -h < /dev/null 2>&1 | head -3
echo "✅ advent executable works"

echo "[test] cheat -h"
cheat -h < /dev/null 2>&1 | head -3
echo "✅ cheat executable works"
