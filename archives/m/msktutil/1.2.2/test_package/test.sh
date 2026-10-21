#!/bin/sh
# test_package/test.sh — smoke test for msktutil 1.2.2 executable
# Contract: sh test.sh <binary> <workdir>
# Runs offline (no Active Directory needed). Emits a deterministic
# "RESULT: P passed, F failed" trailer parsed by test_package/conanfile.py.
set -eu

MSKTUTIL_BIN="${1:?usage: test.sh <msktutil-binary> <workdir>}"
WORKDIR="${2:?usage: test.sh <msktutil-binary> <workdir>}"

# HMFS/HMDFS: /tmp may be read-only and the conan build-tree cwd may be
# inaccessible (getcwd fails). Move to the injected writable scratch dir.
SCRATCH="${TMPDIR:-${TMP:-${TEMP:-$WORKDIR}}}"
mkdir -p "$SCRATCH"
cd "$SCRATCH"

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
}

echo "[test] $MSKTUTIL_BIN --version (exits 0)"
if VERSION_OUT="$("$MSKTUTIL_BIN" --version 2>&1)"; then
    ok "--version exits 0"
else
    bad "--version exits nonzero"
    VERSION_OUT=""
fi

echo "[test] --version output is 'msktutil version 1.2.2'"
if [ "$VERSION_OUT" = "msktutil version 1.2.2" ]; then
    ok "--version prints exact version string"
else
    bad "--version output unexpected: [$VERSION_OUT]"
fi

echo "[test] $MSKTUTIL_BIN --help (exits 0)"
if HELP_OUT="$("$MSKTUTIL_BIN" --help 2>&1)"; then
    ok "--help exits 0"
else
    bad "--help exits nonzero"
    HELP_OUT=""
fi

echo "[test] --help output contains usage text"
case "$HELP_OUT" in
    *"--help"*"Displays this message"*)
        ok "--help prints usage text"
        ;;
    *)
        bad "--help output missing usage text"
        ;;
esac

echo "[test] $MSKTUTIL_BIN --service (missing argument must fail)"
set +e
ERR_OUT="$("$MSKTUTIL_BIN" --service 2>&1)"
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
    ok "--service without argument exits nonzero (rc=$RC)"
else
    bad "--service without argument unexpectedly exits 0"
fi
case "$ERR_OUT" in
    *"Error:"*)
        ok "missing-argument error message present"
        ;;
    *)
        bad "missing-argument error message absent: [$ERR_OUT]"
        ;;
esac

echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
