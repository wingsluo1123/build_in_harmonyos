#!/data/service/hnp/bin/bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

tran list > "${tmp}/scripts.out"
grep -q '^greek$' "${tmp}/scripts.out"

printf 'greek\n' | tran greek > "${tmp}/greek.out"
printf '%s\n' "${tmp}/greek.out"
grep -q 'γρεεκ' "${tmp}/greek.out"

echo "[test] tran consumer checks passed"
