#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ttyrec executables
# Creates a minimal ttyrec recording and runs ttytime on it
set -euo pipefail

_TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_TMPDIR"
TMPFILE="$_TMPDIR/ttyrec-test-$$.log"
trap 'rm -f "$TMPFILE"' EXIT

# Create a minimal ttyrec recording file
# Format: Header(len:int32, tv_sec:long64, tv_usec:long64) + data
printf '\x05\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00hello' > "$TMPFILE"

echo "[step] ttytime on test recording"
ttytime "$TMPFILE" && echo "        [ok] ttytime OK" || {
    echo "        [fail] ttytime failed"
    exit 1
}
