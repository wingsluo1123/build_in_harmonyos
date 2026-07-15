#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for midicsv executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: Test must actually invoke the tested package's binary
set -euo pipefail

TMPDIR="${TMPDIR:-/tmp}"

# Create a minimal valid MIDI file (Format 0, 1 track)
# Header chunk: "MThd" + length(6) + format(0) + tracks(1) + division(384)
# Track chunk: "MTrk" + length(4) + End of Track meta event
python3 -c "
import struct, sys
# MIDI header
header = b'MThd' + struct.pack('>I', 6) + struct.pack('>HHH', 0, 1, 384)
# One track: just End of Track meta event
track_data = b'\x00\xff\x2f\x00'  # delta=0, meta event, end of track, length=0
track = b'MTrk' + struct.pack('>I', len(track_data)) + track_data
sys.stdout.buffer.write(header + track)
" > "$TMPDIR/midicsv_test_in.mid"

CSV1="$TMPDIR/midicsv_test_out1.csv"
MID2="$TMPDIR/midicsv_test_out2.mid"
CSV2="$TMPDIR/midicsv_test_out2.csv"

cleanup() {
    rm -f "$TMPDIR/midicsv_test_in.mid" "$CSV1" "$MID2" "$CSV2"
}
trap cleanup EXIT

echo "[test] midicsv: convert MIDI to CSV"
midicsv "$TMPDIR/midicsv_test_in.mid" "$CSV1"
echo "  ✅ midicsv conversion OK"

echo "[test] csvmidi: convert CSV back to MIDI"
csvmidi "$CSV1" "$MID2"
echo "  ✅ csvmidi conversion OK"

echo "[test] midicsv: round-trip MIDI→CSV→MIDI→CSV"
midicsv "$MID2" "$CSV2"

# The two CSV files should be identical after round-trip
if diff -q "$CSV1" "$CSV2" > /dev/null 2>&1; then
    echo "  ✅ round-trip verified: CSV files match"
else
    echo "  ❌ round-trip failed: CSV files differ"
    exit 1
fi

echo "[test] All tests passed."
