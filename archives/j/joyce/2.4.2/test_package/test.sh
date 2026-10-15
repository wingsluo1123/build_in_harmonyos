#!/bin/sh
# test_package/test.sh - joyce 2.4.2 consumer smoke test.
#
# Real, content-level assertions against the installed dskconv disk-format
# utility (the bundled LibDsk CLI).  This script is the test source file that
# the CI L0c gate requires; it is invoked by test_package/conanfile.py through
# Conan's self.run() (the L0d anti-stub gate).
#
# Output contract: one [PASS]/[FAIL] line per case, then a single deterministic
# summary line
#     RESULT: <passed> passed, <failed> failed
# which the conanfile parses into the HMBS_TEST_PACKAGE_RESULT marker.  The
# counters are maintained in this script only (single source of truth); the
# conanfile never derives counts from stdout text.

set -u

DSKCONV="${1:-dskconv}"

passed=0
failed=0

say() { printf '%s\n' "$*"; }
ok()  { passed=$((passed + 1)); say "[PASS] $1"; }
ko()  { failed=$((failed + 1)); say "[FAIL] $1"; }

# Case 1: dskconv -formats enumerates the supported disk formats and includes
# the PCW/IBM 180k standard format defined by the bundled LibDsk.
out=$("$DSKCONV" -formats 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q "PCW / IBM 180k"; then
    ok "dskconv -formats lists 'PCW / IBM 180k'"
else
    ko "dskconv -formats missing 'PCW / IBM 180k' (rc=$rc)"
fi

# Case 2: a valid CLI invocation of the installed binary exits 0.
"$DSKCONV" -formats >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    ok "dskconv -formats exits 0"
else
    ko "dskconv -formats exit code $rc"
fi

say "RESULT: $passed passed, $failed failed"

if [ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]; then
    exit 0
fi
exit 1
