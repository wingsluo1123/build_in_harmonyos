#!/usr/bin/env bash
# test_package/test.sh - PLAST 2.3.2 end-to-end consumer test.
#
# Driven by test_package/conanfile.py:
#
#   test.sh <data-dir> <api-test-binary> <package-bin-dir>
#
# Checks:
#   1. the packaged PlastCmd / makeplastdb binaries exist and run;
#   2. a related query finds the reference subject with >= 90% identity;
#   3. a negative control (reversed subject) stays below 90% identity;
#   4. makeplastdb serialises the reference bank;
#   5. the C++ library API consumer program succeeds.
set -euo pipefail

DATA="${1:?usage: test.sh <data-dir> <api-test-binary> <package-bin-dir>}"
API_TEST="${2:?usage: test.sh <data-dir> <api-test-binary> <package-bin-dir>}"
PKG_BIN="${3:?usage: test.sh <data-dir> <api-test-binary> <package-bin-dir>}"

# The packaged executables are addressed by path: the generated run environment
# does not extend PATH on every platform.
if [ -d "$PKG_BIN" ]; then
    PATH="$PKG_BIN:${PATH:-}"
    export PATH
fi

BANK="$DATA/bank.fa"
QUERY="$DATA/query.fa"
CONTROL="$DATA/query_unrelated.fa"

for f in "$BANK" "$QUERY" "$CONTROL"; do
    [ -s "$f" ] || { echo "[FAIL] missing test fixture: $f" >&2; exit 1; }
done

# Scratch directory.  OHOS mounts /tmp read only and TMPDIR is not exported by
# every runner, so fall back on the first writable candidate.
work_base="${TMPDIR:-}"
if [ -z "$work_base" ] || [ ! -d "$work_base" ] || [ ! -w "$work_base" ]; then
    work_base=""
    for candidate in "${HOME:-}/tmp" "${HOME:-}" "${TMPDIR:-/tmp}" /tmp; do
        if [ -d "$candidate" ] && [ -w "$candidate" ]; then
            work_base="$candidate"
            break
        fi
    done
fi
[ -n "$work_base" ] || { echo "[FAIL] no writable scratch directory found" >&2; exit 1; }

WORK="$(mktemp -d "$work_base/plast-test-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
echo "[info] scratch directory: $WORK"

# Everything PLAST spawns (SystemCommand, the tests) has to use it as well.
TMPDIR="$WORK"
export TMPDIR

fail() { echo "[FAIL] $*" >&2; exit 1; }
ok()   { echo "[ OK ] $*"; }

# Largest %identity of a tabulated PLAST result file (0 when there is none).
max_identity() {
    awk -F'\t' 'NF >= 3 && $3 ~ /^[0-9]+(\.[0-9]+)?$/ { if ($3 + 0 > m) m = $3 + 0 }
                END { printf "%.2f", m + 0 }' "$1"
}

# ---------------------------------------------------------------------------
# 1. packaged binaries
# ---------------------------------------------------------------------------
command -v PlastCmd    >/dev/null 2>&1 || fail "PlastCmd is not on PATH"
command -v makeplastdb >/dev/null 2>&1 || fail "makeplastdb is not on PATH"
ok "PlastCmd and makeplastdb are installed in the package bin/ directory"

PlastCmd -h > "$WORK/help.txt" 2>&1 || fail "PlastCmd -h failed"
grep -q -- "-outfmt" "$WORK/help.txt" || fail "PlastCmd -h does not list the PLAST options"
ok "PlastCmd -h prints the PLAST option list"

# ---------------------------------------------------------------------------
# 2. related query must find the reference subject
# ---------------------------------------------------------------------------
PlastCmd -p plastp -i "$QUERY" -d "$BANK" -o "$WORK/related.txt" -e 1e-5 -a 2 \
    || fail "plastp run on the related query returned a non zero status"
grep -q "UBIQ_HUMAN" "$WORK/related.txt" \
    || fail "the reference subject id is missing from the result file"

RELATED_ID="$(max_identity "$WORK/related.txt")"
awk -v v="$RELATED_ID" 'BEGIN { exit !(v >= 90.0) }' \
    || fail "related query best identity ${RELATED_ID}% is below 90%"
ok "related query finds the subject at ${RELATED_ID}% identity"

# ---------------------------------------------------------------------------
# 3. negative control: reversed subject, same composition
# ---------------------------------------------------------------------------
PlastCmd -p plastp -i "$CONTROL" -d "$BANK" -o "$WORK/control.txt" -e 1e-5 -a 2 \
    || fail "plastp run on the negative control returned a non zero status"

CONTROL_ID="$(max_identity "$WORK/control.txt")"
awk -v v="$CONTROL_ID" 'BEGIN { exit !(v < 90.0) }' \
    || fail "negative control best identity ${CONTROL_ID}% is unexpectedly high"
ok "negative control stays at ${CONTROL_ID}% identity"

# ---------------------------------------------------------------------------
# 4. makeplastdb serialises the reference bank
#    (the CLI only auto-detects .fa/.pal/.nal/.pin/.nin banks, so the generated
#     quick reader file is validated on its own)
# ---------------------------------------------------------------------------
cp "$BANK" "$WORK/bank.fa"
makeplastdb -d "$WORK/bank.fa" || fail "makeplastdb returned a non zero status"
[ -s "$WORK/bank.fa.info" ] || fail "makeplastdb did not produce bank.fa.info"
ok "makeplastdb produced a non empty bank.fa.info"

# ---------------------------------------------------------------------------
# 5. C++ library API consumer
# ---------------------------------------------------------------------------
[ -x "$API_TEST" ] || fail "the library API test binary is missing: $API_TEST"
"$API_TEST" "$BANK" "$QUERY" "$WORK/api.txt" || fail "the library API consumer test failed"
ok "C++ library API consumer test passed"

echo "ALL PLAST CONSUMER TESTS PASSED"
