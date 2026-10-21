#!/usr/bin/env bash
set -euo pipefail
PREFIX="${1:?Usage: bash run.sh OPENBLAS_PACKAGE_PREFIX}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/lapack-abi-probe.XXXXXX")"
CXX="${CXX:-clang++}"
echo "Evidence directory: $WORK"
if "$CXX" -std=c++17 -I"$PREFIX/include" "$HERE/probe.cpp" -DRAW_CALL -fsyntax-only >"$WORK/raw-call.log" 2>&1; then
    echo 'FAIL: raw five-argument call unexpectedly accepted'
    exit 1
fi
grep -q 'arguments' "$WORK/raw-call.log"
if "$CXX" -std=c++17 -I"$PREFIX/include" "$HERE/probe.cpp" -DLAPACK_ILP64 -fsyntax-only >"$WORK/ilp64.log" 2>&1; then
    echo 'FAIL: incompatible integer contract unexpectedly accepted'
    exit 1
fi
grep -q 'LP64_REQUIRED' "$WORK/ilp64.log"
"$CXX" -std=c++17 -I"$PREFIX/include" "$HERE/probe.cpp" -L"$PREFIX/lib" -Wl,-rpath,"$PREFIX/lib" -lopenblas -o "$WORK/probe" >"$WORK/build.log" 2>&1
if command -v binary-sign-tool >/dev/null; then
    binary-sign-tool sign -inFile "$WORK/probe" -outFile "$WORK/probe" -selfSign 1 >"$WORK/sign.log" 2>&1
fi
LD_LIBRARY_PATH="$PREFIX/lib:${LD_LIBRARY_PATH:-}" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$WORK/probe" | tee "$WORK/runtime.log"
echo 'PASS: expected argument/integer compile negatives and real vendor-macro numerical checks'
