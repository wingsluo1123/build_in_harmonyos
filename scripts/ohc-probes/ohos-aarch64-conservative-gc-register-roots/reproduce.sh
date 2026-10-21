#!/bin/bash
# Reproduce the AArch64 register-root failure of a conservative collector.
#
#   build gc_root_test.c at -O0/-O1/-O2/-Os against the package under test and
#   run each build several times.  A collector that captures its register roots
#   with the x86_64 "spill dummy arguments" trick passes -O0 and fails from -O1
#   on; a collector that forces the spill through setjmp() passes everywhere.
#
# usage:
#   reproduce.sh --prefix DIR [--lib NAME] [--runs N] [--cc PATH]
#
#   --prefix  installation prefix to test against; must contain include/saclib.h
#             and lib/<lib>.a (or the .a can be given with --archive)
#   --archive explicit path to the static archive (skips --lib lookup)
#   --runs    repetitions per optimisation level (default 3)
#
# Exit code 0 = every level passed; 1 = at least one level failed; 2 = usage or
# environment error.
set -u

PREFIX=
ARCHIVE=
CC=${CC:-cc}
RUNS=3
TMPBASE=${TMPDIR:-/tmp}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix)  PREFIX=${2:-}; shift 2 ;;
        --archive) ARCHIVE=${2:-}; shift 2 ;;
        --runs)    RUNS=${2:-}; shift 2 ;;
        --cc)      CC=${2:-}; shift 2 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

[ -n "$PREFIX" ] || { echo "--prefix is required" >&2; exit 2; }
[ -f "$PREFIX/include/saclib.h" ] || { echo "no include/saclib.h under $PREFIX" >&2; exit 2; }
if [ -z "$ARCHIVE" ]; then
    ARCHIVE=$(ls "$PREFIX"/lib/*.a 2>/dev/null | head -1)
fi
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || { echo "no static archive under $PREFIX/lib" >&2; exit 2; }

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK="$TMPBASE/gc-root-test.$$"
mkdir -p "$WORK" || exit 2
trap 'rm -rf "$WORK"' EXIT INT TERM

echo "prefix : $PREFIX"
echo "archive: $ARCHIVE"
echo "compiler: $CC"
echo

failed_levels=
for opt in -O0 -O1 -O2 -Os; do
    bin="$WORK/t${opt}"
    "$CC" "$opt" -Wall -I"$PREFIX/include" "$HERE/gc_root_test.c" -o "$bin" \
        "$ARCHIVE" -lm 2>"$WORK/cc${opt}.log"
    if [ ! -x "$bin" ]; then
        echo "$opt BUILD FAILED"
        sed -n '1,10p' "$WORK/cc${opt}.log"
        failed_levels="$failed_levels $opt"
        continue
    fi
    pass=0
    for i in $(seq 1 "$RUNS"); do
        if "$bin" -q >/dev/null 2>&1; then pass=$((pass+1)); fi
    done
    printf '%-4s : %d/%d pass\n' "$opt" "$pass" "$RUNS"
    [ "$pass" -eq "$RUNS" ] || failed_levels="$failed_levels $opt"
done

echo
if [ -n "$failed_levels" ]; then
    cat <<EOF
DIAGNOSIS: the collector lost live objects at:$failed_levels

  A conservative collector finds its roots by scanning the stack, so it must
  write every live register into the frame before scanning.  On AArch64
  (AAPCS64) the calling function may keep live values in the callee-saved
  registers x19-x28 across the call, where a stack scan cannot see them; a
  collector that relies on spilling "dummy arguments" (the System V AMD64
  technique) therefore loses them.  -O0 keeps every value in a stack slot and
  hides the defect completely, which is why the -O0 row above passes.

  Also check the scan's lower bound: AAPCS64 gives a leaf function a 16-byte red
  zone below sp, and compilers keep spill slots there, so a scan that starts at
  the collector's own frame address (rather than at the address of a local of
  the function that performs the scan) can miss pointers that a caller spilled
  just before calling in.

  Fix pattern: force the spill with setjmp() -- the ABI requires every
  callee-saved register to survive a setjmp(), so the compiler stores each one
  it uses -- and pass the address of a local of the scanning function as the
  low end of the range.
EOF
    exit 1
fi

echo "PASS: every optimisation level kept all live objects."
exit 0
