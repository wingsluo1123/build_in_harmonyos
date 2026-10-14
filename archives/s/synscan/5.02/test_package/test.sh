#!/data/service/hnp/bin/bash
# test_package/test.sh — synscan 5.02 consumer smoke test (on the device,
# invoked by test_package/conanfile.py under the conanrun env).
#
# synscan's runtime scanning needs a raw socket + libpcap + root, which cannot
# run on the device without elevated privileges.  We therefore run:
#   (A) bin/synscan -V  → prints version, exit 0 (exits in arg parsing, before
#                         the root/raw-socket path)
#   (B) bin/sslog -V    → prints version, exit 0 (same early exit)
#   (C) ./test_synscan_api → compiled consumer that links the packaged
#                         libsynscan.a and runs 20 parse-API assertions
#                         (SYNSCAN_API_* counters; exits 0 iff all pass)
#
# A single deterministic counter (SYNSCAN_TEST_TOTAL/PASS/FAIL) is printed at
# the end; test_package/conanfile.py parses it to emit HMBS_TEST_PACKAGE_RESULT.
#
# Usage: bash test.sh <package_root> <test_binary>
set -u

PKG="$1"
TEST_BIN="$2"
if [ -z "$PKG" ] || [ ! -d "$PKG/bin" ]; then
    echo "FAIL: package root not provided/invalid: '$PKG'"
    exit 2
fi
if [ -z "$TEST_BIN" ] || [ ! -x "$TEST_BIN" ]; then
    echo "FAIL: test binary not provided/executable: '$TEST_BIN'"
    exit 2
fi

pass=0
fail=0
passname=""

# run_case NAME EXPECTED_EXIT COMMAND...
run_case() {
    local name="$1" want="$2"; shift 2
    "$@" >/dev/null 2>&1
    local got=$?
    if [ "$got" -eq "$want" ]; then
        pass=$((pass+1)); passname="${passname} ${name}"
        echo "[PASS] $name (exit=$got)"
    else
        fail=$((fail+1))
        echo "[FAIL] $name (want exit=$want, got=$got)"
    fi
}

# (A) synscan -V -> version, exit 0
if [ -x "$PKG/bin/synscan" ]; then
    run_case "synscan -V" 0 "$PKG/bin/synscan" -V
else
    echo "[FAIL] synscan binary missing: $PKG/bin/synscan"; fail=$((fail+1))
fi

# (B) sslog -V -> version, exit 0
if [ -x "$PKG/bin/sslog" ]; then
    run_case "sslog -V" 0 "$PKG/bin/sslog" -V
else
    echo "[FAIL] sslog binary missing: $PKG/bin/sslog"; fail=$((fail+1))
fi

# (C) linked parse-API consumer (20 assertions inside test_synscan_api)
if "$TEST_BIN" >/dev/null 2>&1; then
    pass=$((pass+1)); passname="${passname} parse-API(20)"
    echo "[PASS] parse-API consumer (20 assertions)"
else
    fail=$((fail+1))
    echo "[FAIL] parse-API consumer (test_synscan_api)"
fi

# ---- summary (deterministic source for test_package/conanfile.py) ----
total=$((pass+fail))
echo "SYNSCAN_TEST_TOTAL=$total"
echo "SYNSCAN_TEST_PASS=$pass"
echo "SYNSCAN_TEST_FAIL=$fail"
if [ "$fail" -eq 0 ] && [ "$total" -gt 0 ]; then
    echo "synscan consumer test: ALL PASS ($pass/$total)$passname"
    exit 0
else
    echo "synscan consumer test: FAILED (pass=$pass fail=$fail total=$total)"
    exit 1
fi
