#!/usr/bin/env bash
# LIGGGHTS functional test (Conan test_package).
#
# Runs the packaged DEM engine (bin/lmp_mpi, put on PATH by VirtualRunEnv) on a
# deterministic granular deck and asserts on what the solver actually reports:
#
#   1. bin/lmp_mpi is installed and executable
#   2. the run reaches the requested final step and exits 0
#   3. the thermo output reports exactly the 125 particles of the data file
#   4. the final kinetic energy is a finite, non-zero number
#      (=> contact forces were integrated; NaN/Inf would mean an exploding solver)
#   5. the log contains no LIGGGHTS ERROR
#
# Only bash builtins + grep are used (both available on OHOS images).

set -euo pipefail

ENGINE="${LIGGGHTS_ENGINE:-lmp_mpi}"
EXPECTED_ATOMS="${LIGGGHTS_EXPECTED_ATOMS:-125}"
FINAL_STEP="${LIGGGHTS_FINAL_STEP:-1000}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$TEST_DIR/liggghts_test.log"

fail() {
    echo "[fail] $1"
    if [ -f "$LOG" ]; then
        echo "---- last 20 log lines ----"
        tail -n 20 "$LOG"
        echo "---------------------------"
    fi
    exit 1
}

is_number() {
    case "$1" in
        *[nN]an*|*[iI]nf*) return 1 ;;
    esac
    printf '%s\n' "$1" | grep -Eq '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
}

is_zero() {
    printf '%s\n' "$1" | grep -Eq '^0(\.0*)?$'
}

# ── 1. the packaged engine must be present ──────────────────────────────────
if ! command -v "$ENGINE" >/dev/null 2>&1; then
    fail "$ENGINE is not on PATH - the package binary was not installed"
fi
echo "[test] engine      : $(command -v "$ENGINE")"

# ── 2. run the deterministic granular deck ──────────────────────────────────
rm -f "$LOG"
set +e
"$ENGINE" -in "$TEST_DIR/test_liggghts.in" -log "$LOG" -screen none
RC=$?
set -e
[ "$RC" -eq 0 ] || fail "engine exited with status $RC"
[ -s "$LOG" ] || fail "engine produced no log file"

grep -Fq "Loop time of" "$LOG" || fail "run did not complete (no 'Loop time of' banner)"
if grep -Eq '^(ERROR|\*\*\* ERROR)' "$LOG"; then
    fail "LIGGGHTS reported an error"
fi

# ── 3./4. assert on the reported physics ────────────────────────────────────
# `|| true`: with `set -e` a failing command substitution in an assignment aborts
# the script, which would skip the explicit [fail] message below.
ROW="$(grep -E "^[[:space:]]*${FINAL_STEP}[[:space:]]" "$LOG" | grep -E "[[:space:]]${EXPECTED_ATOMS}[[:space:]]" | tail -n 1 || true)"
[ -n "$ROW" ] || fail "no thermo row for step $FINAL_STEP with $EXPECTED_ATOMS atoms"

set -- $ROW
STEP="$1"; ATOMS="$2"; KE="$3"

echo "[test] final thermo: step=$STEP atoms=$ATOMS ke=$KE"
[ "$STEP" = "$FINAL_STEP" ] || fail "expected step $FINAL_STEP, got $STEP"
[ "$ATOMS" = "$EXPECTED_ATOMS" ] || fail "expected $EXPECTED_ATOMS atoms, got $ATOMS"
is_number "$KE" || fail "kinetic energy is not a finite number: $KE"
if is_zero "$KE"; then
    fail "kinetic energy is zero - contact forces were never integrated"
fi

echo "[pass] lmp_mpi ran the granular deck to step $STEP with $ATOMS particles (ke=$KE)"