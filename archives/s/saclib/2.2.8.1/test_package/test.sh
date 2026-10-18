#!/bin/sh
# test_package/test.sh — drive the compiled consumers of the installed package.
#
# Three binaries are built by test_package/conanfile.py and driven here:
#
#   saclib_test   assertion suite (exact big-integer invariants, list/heap
#                 operations and explicit GC() calls) -- unit-level checks
#   consumer_flow one complete consumer workflow: it reads a problem file and
#                 does a whole job end to end (exact factorial, exact rational
#                 arithmetic, decimal expansion with cycle detection), printing
#                 results that are checked against outside values
#   sample_test   the upstream sample, the only runnable artefact SACLIB ships
#
# It is deliberately /bin/sh compatible: on OHOS it is executed through the bash
# named by $CONFIG_SHELL (see test_package/conanfile.py), and on Linux builders
# it is executed directly.
set -eu

echo "[test] saclib consumer test binary"
ls -l saclib_test
if [ ! -x saclib_test ]; then
    echo "FAIL: saclib_test was not produced or is not executable"
    exit 1
fi

echo "[test] running the functional test"
./saclib_test

# ── complete consumer workflow ────────────────────────────────────────────────
# Expected values (checked here, computed outside SACLIB):
#   11! = 39916800
#   100/3 + 7/13 = 1321/39      100/3 - 7/13 = 1279/39
#   100/3 * 7/13 = 700/39       100/3 / 7/13 = 1300/21
#   1/7 = 0.142857 with a cycle of length 6, 1/2 = 0.5 terminating
if [ -x consumer_flow ]; then
    echo "[test] consumer workflow (exact factorial / rational / decimal)"
    # the problem is fed through stdin: /tmp is not writable on OHOS
    flow=$(printf '# nfact b1 c1 b2 c2\n11 100 3 7 13\n' | ./consumer_flow -)
    printf '%s\n' "$flow"

    printf '%s' "$flow" | grep -q '11! = 39916800' \
        || { echo "FAIL: consumer flow computed the wrong factorial"; exit 1; }
    printf '%s' "$flow" | grep -q 'x+y = 1321/39' \
        || { echo "FAIL: consumer flow x+y wrong"; exit 1; }
    printf '%s' "$flow" | grep -q 'x-y = 1279/39' \
        || { echo "FAIL: consumer flow x-y wrong"; exit 1; }
    printf '%s' "$flow" | grep -q 'x\*y = 700/39' \
        || { echo "FAIL: consumer flow x*y wrong"; exit 1; }
    printf '%s' "$flow" | grep -q 'x/y = 1300/21' \
        || { echo "FAIL: consumer flow x/y wrong"; exit 1; }
    printf '%s' "$flow" | grep -q '1/7   = 0.142857  (cycle of length 6)' \
        || { echo "FAIL: consumer flow decimal expansion/cycle wrong"; exit 1; }
    printf '%s' "$flow" | grep -q '1/3   = 0.3  (cycle of length 1)' \
        || { echo "FAIL: consumer flow repeating decimal wrong"; exit 1; }
    printf '%s' "$flow" | grep -q '1/2   = 0.5  (terminating)' \
        || { echo "FAIL: consumer flow terminating decimal wrong"; exit 1; }
    printf '%s' "$flow" | grep -q 'equal: yes' \
        || { echo "FAIL: consumer flow closing identity does not hold"; exit 1; }
    printf '%s' "$flow" | grep -q 'PASS - consumer workflow finished' \
        || { echo "FAIL: consumer workflow reported a problem"; exit 1; }
    echo "  ok: consumer workflow results match the expected values"
else
    echo "FAIL: consumer_flow was not produced"
    exit 1
fi

# ── upstream sample ───────────────────────────────────────────────────────────
# doc/user_guide/sample.c is the only runnable artefact SACLIB ships (it has no
# test suite at all, see notes.md §4).  It is also the only upstream code that
# uses the sacMain() hook, so building and driving it verifies the weak-symbol
# handling of patches/0002 from the consumer side.
if [ -x sample_test ]; then
    echo "[test] upstream sample (doc/user_guide/sample.c)"
    out=$(printf '12345678901234567890\n98765432109876543210\n5\n' | ./sample_test)
    printf '%s\n' "$out"
    printf '%s' "$out" | grep -q '1219326311370217952237463801111263526900' \
        || { echo "FAIL: upstream sample computed the wrong product"; exit 1; }
    printf '%s' "$out" | grep -q 'Repeating the above computation 5 times' \
        || { echo "FAIL: upstream sample did not run its loop"; exit 1; }
    echo "  ok: exact 20x20-digit product, sacMain hook used"
else
    echo "FAIL: sample_test was not produced"
    exit 1
fi

echo "[test] all saclib consumer tests passed"
