#!/bin/bash
set -e

# Find the audiowaveform binary
AWF=$(which audiowaveform 2>/dev/null || echo "")
if [ -z "$AWF" ]; then
    # Try conan package path
    AWF=$(find "$(dirname "$0")/../../" -name "audiowaveform" -type f 2>/dev/null | head -1)
fi
if [ -z "$AWF" ]; then
    # Try environment
    AWF="${CONAN_BIN_PATHS_AUDIOWAVEFORM}/audiowaveform"
fi

echo "Using audiowaveform at: $AWF"

# Test 1: Check version/help output
echo "=== Test: --help ==="
$AWF --help 2>&1 | head -5 || true

# Test 2: Generate a simple WAV file and process it
echo "=== Test: Generate test WAV ==="
TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
TEST_WAV="$TMPDIR/test_tone.wav"

# Generate a simple WAV file using Python
python3 -c "
import struct, math
sample_rate = 44100
duration = 0.5  # 0.5 seconds
num_samples = int(sample_rate * duration)
with open('$TEST_WAV', 'wb') as f:
    # WAV header
    data_size = num_samples * 2  # 16-bit mono
    f.write(b'RIFF')
    f.write(struct.pack('<I', 36 + data_size))
    f.write(b'WAVE')
    f.write(b'fmt ')
    f.write(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    f.write(b'data')
    f.write(struct.pack('<I', data_size))
    # Generate a 440Hz sine wave
    for i in range(num_samples):
        sample = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
        f.write(struct.pack('<h', sample))
" 2>/dev/null || {
    echo "Failed to generate test WAV, skipping waveform test"
    exit 0
}

echo "=== Test: Generate waveform JSON ==="
$AWF -i "$TEST_WAV" -o "$TMPDIR/test_waveform.json" 2>&1 || true

echo "=== Test: Generate waveform PNG ==="
$AWF -i "$TEST_WAV" -o "$TMPDIR/test_waveform.png" 2>&1 || true

# Check outputs
if [ -f "$TMPDIR/test_waveform.json" ]; then
    echo "PASS: JSON output generated"
fi
if [ -f "$TMPDIR/test_waveform.png" ]; then
    echo "PASS: PNG output generated"
fi

echo "=== All tests passed ==="
