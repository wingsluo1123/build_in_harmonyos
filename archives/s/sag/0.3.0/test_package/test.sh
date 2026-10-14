#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for sag executable (offline-safe).
set -eu

# HMBS readonly /tmp compat
if [ -z "${TMPDIR:-}" ] || [ "$TMPDIR" = "0" ] || [ "$TMPDIR" = "/tmp" ] || [ ! -d "$TMPDIR" ] || [ ! -w "$TMPDIR" ]; then
  _hmbs_tmp=""
  for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "${HMBS_TMPDIR:-}"; do
    if [ -n "${_cand:-}" ] && [ -d "$_cand" ] && [ -w "$_cand" ]; then _hmbs_tmp="$_cand"; break; fi
  done
  if [ -z "$_hmbs_tmp" ]; then
    _hmbs_tmp="/data/storage/el2/base/haps/entry/files/tmp"
    mkdir -p "$_hmbs_tmp" 2>/dev/null || true
    if [ ! -d "$_hmbs_tmp" ] || [ ! -w "$_hmbs_tmp" ]; then
      _hmbs_tmp="$PWD/tmp"
      mkdir -p "$_hmbs_tmp" 2>/dev/null || true
    fi
  fi
  TMPDIR="$_hmbs_tmp"
  export TMPDIR
fi
export TMP="${TMP:-$TMPDIR}"
export TEMP="${TEMP:-$TMPDIR}"
mkdir -p "$TMPDIR" 2>/dev/null || true

echo "[test] TMPDIR=$TMPDIR TMP=$TMP TEMP=$TEMP"

echo "[test 1/3] sag -V returns version 0.3.0"
sag -V 2>&1 | tee /tmp/sag_v.txt 2>/dev/null || sag -V
sag -V 2>&1 | grep -q "0.3.0" && echo "        [ok] version contains 0.3.0" || { echo "        [fail] version mismatch"; exit 1; }

echo "[test 2/3] sag --help succeeds"
sag --help > /dev/null 2>&1 && echo "        [ok] --help passed" || { echo "        [fail] --help failed"; exit 1; }

echo "[test 3/3] sag prompting prints offline guide"
sag prompting 2>&1 | grep -qi "prompt" && echo "        [ok] prompting guide printed" || { echo "        [fail] prompting failed"; exit 1; }

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":3,"passedCount":3}'
