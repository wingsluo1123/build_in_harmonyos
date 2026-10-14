#!/bin/sh
# test_package/test.sh — functional smoke test for rawrec executable.
# Runs in conanrun env (PATH includes installed bin/). POSIX sh compatible.
set -eu

PASS_COUNT=0
DISCOVERED=3

echo "[test 1/3] rawrec --version"
if rawrec --version 2>&1 | grep -q "version 0.9.99"; then
  echo "[ok] --version prints expected version string"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "[fail] --version output mismatch" >&2
  exit 1
fi

echo "[test 2/3] rawrec --help"
if rawrec --help >/dev/null 2>&1; then
  echo "[ok] --help exits successfully"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "[fail] --help non-zero exit" >&2
  exit 1
fi

echo "[test 3/3] rawplay --version (alt invocation symlink)"
if rawplay --version 2>&1 | grep -q "version 0.9.99"; then
  echo "[ok] rawplay symlink works"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "[fail] rawplay symlink broken" >&2
  exit 1
fi

echo "[summary] ${PASS_COUNT}/${DISCOVERED} test_package cases passed"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test.sh (rawrec --version, rawrec --help, rawplay --version)\",\"discovered\":3,\"passedCount\":3}"
