#!/bin/sh
set -eu

echo "Running test() — mrbuild consumer test"

# 1) installed payload (static checks)
test -f "$MRBUILD_DIR/Makefile.common.header"
test -f "$MRBUILD_DIR/Makefile.common.footer"
test -f "$MRBUILD_BINDIR/make-pod-from-help"
test -x "$MRBUILD_BINDIR/make-pod-from-help"
head -1 "$MRBUILD_BINDIR/make-pod-from-help" | grep -q "perl"
echo "ok: installed payload present (templates + executable perl script)"

# 2) functional: build a real mini project with the installed templates
cd project
make
# shared library artifacts (symlink chain: libmrtest.so -> .so.0 -> .so.0.1)
test -f libmrtest.so.0.1
test -L libmrtest.so
test -L libmrtest.so.0
head -c 4 libmrtest.so.0.1 | od -An -tx1 | tr -d " \n" | grep -q "7f454c46"
# executable artifact
test -x run
head -c 4 run | od -An -tx1 | tr -d " \n" | grep -q "7f454c46"
echo "ok: template build produced libmrtest.so.0.1 + run (real ELF artifacts)"

# 3) make-pod-from-help dynamic behaviour (when perl is available on the runner)
cd ..
if command -v perl >/dev/null 2>&1; then
  if perl "$MRBUILD_BINDIR/make-pod-from-help" 2>err.txt; then
    echo "FAIL: make-pod-from-help must reject a missing argument"
    exit 1
  fi
  grep -q "Need exactly one argument" err.txt
  grep -q "Usage:" err.txt
  rm -f err.txt
  echo "ok: make-pod-from-help runs under perl and enforces its usage contract"
else
  echo "note: perl not available on this runner; script verified statically (shebang + exec bit)"
fi

echo "PASS: mrbuild consumer test"
