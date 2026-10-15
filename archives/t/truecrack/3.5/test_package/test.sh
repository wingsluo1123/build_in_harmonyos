#!/bin/sh
# test_package/test.sh — smoke test for truecrack executable
# Runs in conanrun env (PATH includes installed bin/).
#
# Emits the HMBS_TEST_PACKAGE_RESULT hard-gate JSON marker from the real,
# deterministic per-case result (truecrack -h prints usage and exits 0).
# Counts come from the discrete CHECK steps below, not from any inferred total.
set -eu

cmd='truecrack -h'
passed=0
failed=0

echo "[test] truecrack -h (print usage, exit 0)"
if out="$(truecrack -h 2>&1)"; then
    if echo "$out" | grep -q "Usage"; then
        echo "[test] OK: truecrack usage printed successfully"
        passed=$((passed + 1))
    else
        echo "[test] FAIL: truecrack -h did not print usage"
        failed=$((failed + 1))
    fi
else
    echo "[test] FAIL: truecrack -h exited nonzero"
    failed=$((failed + 1))
fi

# discovered = number of discrete checks declared in this smoke test = 1
discovered=1
if [ "$failed" -ne 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"$cmd\",\"discovered\":$discovered,\"passedCount\":$passed}"
    exit 1
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"$cmd\",\"discovered\":$discovered,\"passedCount\":$passed}"
exit 0
