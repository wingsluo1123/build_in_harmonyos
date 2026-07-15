#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for daemontools executables.
# Runs in the conanrun env, so PATH includes the installed bin/.
set -euo pipefail

echo "[step] tai64n — add TAI64N timestamp to input line"
echo "hello" | tai64n | grep "hello"

echo "[step] tai64nlocal — convert TAI64N back to local time"
echo "hello" | tai64n | tai64nlocal | grep "hello"

echo "[step] svstat — error handling for nonexistent service path"
svstat /nonexistent 2>&1 | grep -q "unable to chdir"

echo "daemontools test_package: PASS"
