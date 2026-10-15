#!/bin/sh
# test_package consumer test for perdition 2.2.
# 2 real checks against the installed package binaries.
# Each passing check prints exactly one `ok N: ...` line (deterministic source
# for HMBS_TEST_PACKAGE_RESULT counting in conanfile.py).
# Uses only POSIX sh + installed binaries; no compiler needed.
set -u

PASS=0
FAIL=0

check_ok() {
  echo "ok $1: $2"
  PASS=$((PASS + 1))
}

check_fail() {
  echo "not ok: $2"
  FAIL=$((FAIL + 1))
}

# --- check 1: perdition binary runs and prints proxy usage ---
HELP_OUT=""
if command -v perdition >/dev/null 2>&1; then
  HELP_OUT=$(perdition --help 2>&1)
else
  HELP_OUT=""
fi
case "$HELP_OUT" in
  *"mail retrieval proxy"*)
    check_ok 1 "perdition --help shows proxy banner"
    ;;
  *)
    check_fail 1 "perdition --help missing proxy banner"
    ;;
esac

# --- check 2: makegdbm gdbm roundtrip (write then read back) ---
WORKDIR="hmbs-perdition-test"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
ROUNDTRIP_OK=0
if command -v makegdbm >/dev/null 2>&1; then
  if printf 'alice:mail.example.com\n' | makegdbm "$WORKDIR/map.gdbm" 2>"$WORKDIR/mk.err"; then
    if [ -f "$WORKDIR/map.gdbm" ]; then
      UNDO_OUT=$(makegdbm -u "$WORKDIR/map.gdbm" 2>"$WORKDIR/undo.err")
      case "$UNDO_OUT" in
        *"alice"*"mail.example.com"*)
          ROUNDTRIP_OK=1
          ;;
      esac
    fi
  fi
fi
if [ "$ROUNDTRIP_OK" = "1" ]; then
  check_ok 2 "makegdbm roundtrip alice:mail.example.com"
else
  check_fail 2 "makegdbm roundtrip failed"
fi
rm -rf "$WORKDIR"

echo "test perdition 2.2: $PASS/2 checks PASS, $FAIL failed"
if [ "$PASS" = "2" ] && [ "$FAIL" = "0" ]; then
  echo "ALL CHECKS PASSED"
  exit 0
else
  echo "CONSUMER TEST FAILED"
  exit 1
fi
