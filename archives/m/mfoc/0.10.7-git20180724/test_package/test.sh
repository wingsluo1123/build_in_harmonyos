#!/data/service/hnp/bin/bash
# test_package/test.sh - smoke test for mfoc executable
# Runs in conanrun env (PATH includes installed bin/).
# MUST be executed with a real bash (e.g. /data/service/hnp/bin/bash):
# OHOS /system/bin/sh (mksh) cannot execute ELF binaries (fails with 127).
# Uses `set -u` only (no `set -e`): every tested binary invocation is wrapped
# with `set +e` + explicit rc capture, so a non-zero exit can never abort the
# script before diagnostics and the rc assertion run.
set -u

MFOC_BIN="${1:-mfoc}"
if [ -n "${CONAN_MFOC_BIN:-}" ]; then
  MFOC_BIN="${CONAN_MFOC_BIN}"
fi

echo "[test] mfoc binary: ${MFOC_BIN}"
echo "[test] invoking shell: ${SHELL:-unknown} ($0)"

case "${MFOC_BIN}" in
  */*)
    if [ ! -x "${MFOC_BIN}" ]; then
      echo "FAIL: mfoc binary not executable: ${MFOC_BIN}"
      ls -l "${MFOC_BIN}" || true
      exit 1
    fi
    ;;
  *)
    if ! command -v "${MFOC_BIN}" >/dev/null 2>&1; then
      echo "FAIL: mfoc not found in PATH: ${MFOC_BIN}"
      echo "PATH=${PATH:-(empty)}"
      exit 1
    fi
    ;;
esac

echo "[test] mfoc -h"
set +e
"${MFOC_BIN}" -h > mfoc_help.txt 2>&1
rc=$?
set -u
echo "[test] exit code: ${rc}"
cat mfoc_help.txt
if [ "${rc}" -ne 0 ]; then
  echo "FAIL: mfoc -h exit ${rc} != 0"
  echo "[diag] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-(empty)}"
  ls -l "${MFOC_BIN}" 2>/dev/null || true
  command -v file >/dev/null 2>&1 && file "${MFOC_BIN}" || true
  command -v ldd >/dev/null 2>&1 && ldd "${MFOC_BIN}" || true
  exit 1
fi
if [ ! -s mfoc_help.txt ]; then
  echo "FAIL: mfoc -h produced empty output (harness would false-pass)"
  exit 1
fi
grep -q "Usage" mfoc_help.txt || { echo "FAIL: Usage not in -h output"; exit 1; }
grep -q "0.10.7" mfoc_help.txt || { echo "FAIL: version 0.10.7 not in -h output"; exit 1; }

# Negative control: missing mandatory -O must fail (proves harness detects failure)
set +e
"${MFOC_BIN}" > mfoc_noargs.txt 2>&1
rc2=$?
set -u
echo "[test] no-args exit code: ${rc2} (expected non-zero)"
cat mfoc_noargs.txt
if [ "${rc2}" -eq 0 ]; then
  echo "FAIL: mfoc without args should fail"
  exit 1
fi
echo "PASS: mfoc smoke test (discovered=1 passed=1)"
