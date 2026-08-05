#!/bin/bash
set -e

AWF=$(which audiowaveform 2>/dev/null || echo "")
if [ -z "$AWF" ]; then
    AWF="${CONAN_BIN_PATHS_AUDIOWAVEFORM}/audiowaveform"
fi
echo "Using audiowaveform at: $AWF"

# Test 1: Check --help works
$AWF --help 2>&1 | head -5

# Test 2: Generate a test WAV file
TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
rm -f "$TMPDIR/test_waveform.json" "$TMPDIR/test_waveform.png"
TEST_WAV="$TMPDIR/test_tone.wav"

python3 -c "
import struct, math
sr = 44100; dur = 0.5; n = int(sr * dur)
with open('$TEST_WAV', 'wb') as f:
    ds = n * 2
    f.write(b'RIFF'); f.write(struct.pack('<I', 36 + ds)); f.write(b'WAVE')
    f.write(b'fmt '); f.write(struct.pack('<IHHIIHH', 16, 1, 1, sr, sr * 2, 2, 16))
    f.write(b'data'); f.write(struct.pack('<I', ds))
    for i in range(n):
        f.write(struct.pack('<h', int(32767 * math.sin(2 * math.pi * 440 * i / sr))))
" || { echo "FAIL: WAV generation failed"; exit 1; }

# Test 3: Generate waveform JSON
$AWF -i "$TEST_WAV" -o "$TMPDIR/test_waveform.json" 2>&1 || { echo "FAIL: audiowaveform JSON generation failed"; exit 1; }
[ -f "$TMPDIR/test_waveform.json" ] && echo "PASS: JSON output generated" || { echo "FAIL: JSON output not found"; exit 1; }

# Test 4: Generate waveform PNG
$AWF -i "$TEST_WAV" -o "$TMPDIR/test_waveform.png" 2>&1 || { echo "FAIL: audiowaveform PNG generation failed"; exit 1; }
[ -f "$TMPDIR/test_waveform.png" ] && echo "PASS: PNG output generated" || { echo "FAIL: PNG output not found"; exit 1; }

echo "=== All tests passed ==="
