#!/usr/bin/env bash
# Functional consumer test for the packaged vbindiff binary.
#
# vbindiff is an interactive curses program, so this suite drives the
# deterministic paths that exit before the terminal input loop is entered:
# version, license, help, unknown-option and arity handling, plus the failure
# path for unreadable files.  Every invocation runs against the packaged
# binary by absolute path and is wrapped in a timeout, so a path that is
# supposed to exit cannot leave the build or a CI worker blocked on the
# interactive loop.  Exit codes and printed contract text are asserted, not
# just printed.
set -u

BIN="${1:?usage: test_vbindiff.sh <absolute path to the packaged vbindiff>}"
WORK="${PWD}/vbindiff-test-output"
mkdir -p "$WORK"

HAVE_TIMEOUT=0
command -v timeout >/dev/null 2>&1 && HAVE_TIMEOUT=1

run_bin() {
  if [ "$HAVE_TIMEOUT" = 1 ]; then
    timeout 20 "$BIN" "$@"
  else
    "$BIN" "$@"
  fi
}

PASS=0
FAILED=0

record() {
  if [ "$1" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "ok - $2"
  else
    FAILED=$((FAILED + 1))
    echo "NOT OK - $2"
  fi
}

echo "== consumer test: $BIN (timeout guard: $HAVE_TIMEOUT) =="

# A1 + A2: -V must exit 0 and report the version string produced by our own
# configure run, which proves the packaged binary is the one just built.
rc=0
run_bin -V >"$WORK/version.out" 2>"$WORK/version.err" || rc=$?
[ "$rc" -eq 0 ]
record $? "A1 'vbindiff -V' exits 0 (rc=$rc)"
grep -q 'VBinDiff 3.0_beta5' "$WORK/version.out"
record $? "A2 'vbindiff -V' prints the built PACKAGE_VERSION (VBinDiff 3.0_beta5)"

# A3: the long-option table and the usage contract are linked in.
rc=0
run_bin --help >"$WORK/help.out" 2>"$WORK/help.err" || rc=$?
{ [ "$rc" -eq 0 ] && grep -q 'FILE1 \[FILE2\]' "$WORK/help.out"; }
record $? "A3 'vbindiff --help' exits 0 and prints the FILE1 [FILE2] usage line (rc=$rc)"

# A4: the license handler reaches the GPL text embedded in the binary.
rc=0
run_bin -L >"$WORK/license.out" 2>"$WORK/license.err" || rc=$?
{ [ "$rc" -eq 0 ] && grep -q 'GNU General Public License' "$WORK/license.out"; }
record $? "A4 'vbindiff -L' exits 0 and prints the GNU General Public License text (rc=$rc)"

# A5: an unknown option is reported through the usage path with status 1.
rc=0
run_bin --definitely-not-an-option >"$WORK/badopt.out" 2>"$WORK/badopt.err" || rc=$?
{ [ "$rc" -eq 1 ] && grep -q 'Usage:' "$WORK/badopt.out"; }
record $? "A5 unknown option exits 1 and prints usage (rc=$rc)"

# A6: no operands takes the arity path, which prints help and exits 0.
rc=0
run_bin >"$WORK/noargs.out" 2>"$WORK/noargs.err" || rc=$?
{ [ "$rc" -eq 0 ] && grep -q 'Usage:' "$WORK/noargs.out"; }
record $? "A6 no operands exits 0 and prints usage (rc=$rc)"

# A7: two unreadable operands fail with a non-zero status and a message on
# stderr.  The message differs by platform (vbindiff reports "Unable to
# initialize windows" when curses cannot open the terminal, otherwise it
# reports "Unable to open <file>"), so the hard assertions are the exit
# status and that stderr carries the reason; the captured text is echoed
# below for the record.
rc=0
run_bin "$WORK/absent-file-a" "$WORK/absent-file-b" >"$WORK/missing.out" 2>"$WORK/missing.err" || rc=$?
{ [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] && [ -s "$WORK/missing.err" ]; }
record $? "A7 unreadable operands exit non-zero (rc=$rc) and write a reason to stderr"

echo "== captured evidence =="
for f in version help license badopt noargs missing; do
  for stream in out err; do
    file="$WORK/$f.$stream"
    [ -s "$file" ] || continue
    echo "--- $f.$stream ---"
    sed -n '1,6p' "$file"
  done
done

echo "== consumer assertions: passed=$PASS failed=$FAILED =="
if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
exit 0
