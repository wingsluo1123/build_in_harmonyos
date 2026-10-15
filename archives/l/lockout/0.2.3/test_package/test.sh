#!/data/service/hnp/bin/bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

lockout status > "${tmp}/status.out"
grep -q 'not locked' "${tmp}/status.out"

if lockout > "${tmp}/usage.out" 2>&1; then
  echo "[fail] lockout unexpectedly accepted no arguments"
  exit 1
fi
grep -q 'lockout version 0.2.3' "${tmp}/usage.out"
grep -q 'STATUS (any user)' "${tmp}/usage.out"

echo "[test] lockout consumer checks passed"
