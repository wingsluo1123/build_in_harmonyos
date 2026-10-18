#!/data/service/hnp/bin/bash
# test_package/test_xlispstat.sh - consumer smoke test for xlispstat 3.52.23.
# Runs in conanrun env: PATH includes <pkg>/bin and XLISPLIB points to
# <pkg>/share/xlispstat (patched wrapper honors the inherited XLISPLIB).
set -u

# xlisp GC mark recursion needs more stack than the device default; the
# wrapper's own mksh ulimit is a no-op, so raise it here (this script runs
# under hnp bash) and let every xlispstat child inherit it.
ulimit -s unlimited 2>/dev/null || ulimit -s 65536 2>/dev/null || true

# The hnp bash getcwd defect makes $(pwd) unreliable; probe for a writable
# scratch directory instead of assuming the cwd or /tmp.
out_file=""
for d in "$HOME" "${TMPDIR:-}" "/data/local/tmp"; do
  if [ -n "$d" ] && touch "$d/.xls-tp-probe" 2>/dev/null; then
    rm -f "$d/.xls-tp-probe"
    out_file="$d/xlispstat-tp-out.txt"
    break
  fi
done
if [ -z "$out_file" ]; then
  echo "[FAIL] no writable scratch directory found"
  exit 1
fi

pass=0
fail=0

check() {
  local desc="$1"; shift
  if "$@"; then
    echo "[ok] $desc"
    pass=$((pass + 1))
  else
    echo "[FAIL] $desc"
    fail=$((fail + 1))
  fi
}

command -v xlispstat >/dev/null 2>&1
XL="$XLISPLIB/xlisp"
WKS="$XLISPLIB/xlisp.wks"
check "wrapper script shipped in bin/" test -f "${XLISPLIB%share/*}bin/xlispstat"

check "XLISPLIB runtime env exported" test -d "${XLISPLIB:-/nonexistent}"
check "default workspace shipped" test -f "${XLISPLIB:-/nonexistent}/xlisp.wks"
check "interpreter binary shipped" test -f "${XLISPLIB:-/nonexistent}/xlisp"
check "Data directory shipped" test -d "${XLISPLIB:-/nonexistent}/Data"

# Startup banner must identify XLISP-STAT 3.52.23 (output written to a file;
# embedding captured output in inline bash -c strings is broken by the hnp
# bash getcwd noise containing apostrophes).
printf '(exit)\n' | "$XL" -w"$WKS" > "$out_file" 2>&1 || true
head -5 "$out_file"
check "banner announces XLISP-STAT" grep -qi 'XLISP-STAT' "$out_file"
check "banner announces version 3.52.23" grep -q '3\.52\.23' "$out_file"

printf '(+ 1 2) (exit)\n' | "$XL" -w"$WKS" > "$out_file" 2>&1 || true
check "arithmetic (+ 1 2) => 3" grep -Eq '(^|> )3$' "$out_file"

printf "(mapcar #'+ '(1 2 3) '(10 20 30)) (exit)\n" | "$XL" -w"$WKS" > "$out_file" 2>&1 || true
check "mapcar vectorized add => (11 22 33)" grep -q '(11 22 33)' "$out_file"

printf '(def x (list 1 2 3 4 5)) (mean x) (exit)\n' | "$XL" -w"$WKS" > "$out_file" 2>&1 || true
check "mean of (1 2 3 4 5) => 3" grep -Eq '^3(\.0)?$' "$out_file"

echo "test_package summary: pass=$pass fail=$fail"
test "$fail" -eq 0
