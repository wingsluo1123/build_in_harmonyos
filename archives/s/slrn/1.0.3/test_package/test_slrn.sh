#!/bin/sh
# test_slrn.sh <bindir> <tmpdir>
# Consumer CLI contract tests for the packaged slrn binary.
# Counting unit: independent check items (5 in this script).
set -u

BINDIR="$1"
TMPDIR_TEST="$2"
SLRN="$BINDIR/slrn"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

export TERM="${TERM:-xterm}"
export HOME="${HOME:-$TMPDIR_TEST}"
export TMPDIR="$TMPDIR_TEST"

# Check 1: --help exits 0 and prints the usage banner.
if "$SLRN" --help > "$TMPDIR_TEST/help.out" 2>&1 && \
   grep -q "Usage: slrn" "$TMPDIR_TEST/help.out"; then
    pass "slrn --help prints usage"
else
    fail "slrn --help"
fi

# Check 2: --version exits 0.
if "$SLRN" --version > "$TMPDIR_TEST/version.out" 2>&1; then
    pass "slrn --version exit 0"
else
    fail "slrn --version exit code"
fi

# Check 3: --version reports the packaged upstream version.
if grep -q "^slrn 1\.0\.3" "$TMPDIR_TEST/version.out"; then
    pass "version string is slrn 1.0.3"
else
    fail "version string (got: $(head -1 "$TMPDIR_TEST/version.out"))"
fi

# Check 4: NNTP backend is compiled in (default server object).
if grep -q "+nntp" "$TMPDIR_TEST/version.out"; then
    pass "nntp backend compiled in (+nntp)"
else
    fail "nntp backend missing"
fi

# Check 5: SSL support is compiled in (OpenSSL integration).
if grep -q "+ssl" "$TMPDIR_TEST/version.out"; then
    pass "ssl support compiled in (+ssl)"
else
    fail "ssl support missing"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "test_slrn.sh: FAILURES detected"
    exit 1
fi
echo "test_slrn.sh: all 5 checks passed"
exit 0
