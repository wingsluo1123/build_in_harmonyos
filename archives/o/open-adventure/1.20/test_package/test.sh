#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for open-adventure executables
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] advent -h"
advent -h < /dev/null 2>&1
echo "✅ advent executable works"

echo "[test] cheat -h"
cheat -h < /dev/null 2>&1
echo "✅ cheat executable works"
