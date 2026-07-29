#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ttyrec executables
# Compiles test.c, creates a minimal ttyrec recording, runs ttytime
set -euo pipefail

_TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_TMPDIR"
TMPFILE="$_TMPDIR/ttyrec-test-$$.log"
trap 'rm -f "$TMPFILE" "${_TMPDIR}/test_prog"' EXIT

# Compile and run test.c to verify it works
echo "[step] compile and run test.c"
clang -o "$_TMPDIR/test_prog" "$(dirname "$0")/test.c"
"$_TMPDIR/test_prog" && echo "        [ok] test.c compiled and executed"

# Create a minimal ttyrec recording (2 records)
# Format from io.c read_header: tv_sec(int32 LE) + tv_usec(int32 LE) + len(int32 LE) + data
# Record 1: tv_sec=1, tv_usec=0, len=5, data="hello"
# Record 2: tv_sec=3, tv_usec=0, len=5, data="world"
printf '\x01\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00hello' > "$TMPFILE"
printf '\x03\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00world' >> "$TMPFILE"

echo "[step] ttytime on test recording"
ttytime "$TMPFILE" && echo "        [ok] ttytime OK" || {
    echo "        [fail] ttytime failed"
    exit 1
}
