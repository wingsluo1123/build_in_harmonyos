#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for git-remote-codecommit executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] git-remote-codecommit (no args, expect 'Too few arguments')"
output=$(git-remote-codecommit 2>&1 || true)  # binary exits non-zero with no args, expected behavior
echo "$output"
if echo "$output" | grep -q "Too few arguments"; then
    echo "PASS: git-remote-codecommit is installed and functional"
else
    echo "FAIL: git-remote-codecommit did not produce expected output"
    exit 1
fi
