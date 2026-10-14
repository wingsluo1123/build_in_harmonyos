#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for souffle 2.5
# Runs in conanrun env (PATH includes installed bin/).
# Two real cases:
#   1. `souffle --version` runs and prints version footer.
#   2. An end-to-end Datalog reachability program is evaluated; its output CSV
#      must contain the expected 6 transitive-path tuples (R34 substantive
#      verification of the shipped compiler engine).
#
# Emits the HMBS_TEST_PACKAGE_RESULT machine-evidence marker (hard gate) with
# real counts sourced from the PASSED counter incremented by every case that
# actually ran and passed in this same script.
set -eu

TOTAL=2
PASSED=0

fail_test() {
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh","discovered":%d,"passedCount":%d}\n' \
        "$TOTAL" "$PASSED"
    exit 1
}

echo "[test] case 1: souffle --version"
souffle --version >/dev/null || fail_test
echo "[test] case 1 OK"
PASSED=$((PASSED + 1))

echo "[test] case 2: end-to-end Datalog program (transitive closure)"
souffle -D. -F. test.dl || fail_test

if [ ! -f "path.csv" ]; then
    echo "[test] FAIL: path.csv was not produced"
    fail_test
fi

lines=$(wc -l < path.csv | tr -d '[:space:]')
echo "[test] path.csv lines = ${lines}"
echo "[test] path.csv content:"
cat path.csv

# Edges 1->2,2->3,3->4 give reachability pairs
# (1,2)(2,3)(3,4)(1,3)(2,4)(1,4) = 6 tuples.
if [ "${lines}" != "6" ]; then
    echo "[test] FAIL: expected 6 path rows, got ${lines}"
    fail_test
fi
echo "[test] case 2 OK"
PASSED=$((PASSED + 1))

echo "[test] PASS: ${PASSED}/${TOTAL} test cases passed"

printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh","discovered":%d,"passedCount":%d}\n' \
    "$TOTAL" "$PASSED"
