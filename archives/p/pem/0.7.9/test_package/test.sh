#!/data/service/hnp/bin/bash
set -euo pipefail

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
export HOME="${tmp}/home"
mkdir -p "${HOME}"

pem --version | grep -q 'Pem 0.7.9'
pem -e salary 1000
pem -c food lunch 20

pem -s > "${tmp}/daily.out"
grep -q 'salary' "${tmp}/daily.out"
grep -q 'lunch' "${tmp}/daily.out"
grep -q '1000.00' "${tmp}/daily.out"
grep -q '20.00' "${tmp}/daily.out"

pem -m > "${tmp}/monthly.out"
grep -q '1000.00' "${tmp}/monthly.out"
grep -q '20.00' "${tmp}/monthly.out"

pem -C > "${tmp}/category.out"
grep -q 'food' "${tmp}/category.out"
grep -q '20.00' "${tmp}/category.out"

echo "[test] pem consumer checks passed"
