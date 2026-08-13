#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gettext executables
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] envsubst --version"
envsubst --version | head -1 || { echo "FAIL"; exit 1; }
echo "[test] gettext --version"
gettext --version | head -1 || { echo "FAIL"; exit 1; }
