#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gettext executables
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] envsubst --version"
envsubst --version | head -1 && echo "OK"
echo "[test] gettext --version"
gettext --version | head -1 && echo "OK"
