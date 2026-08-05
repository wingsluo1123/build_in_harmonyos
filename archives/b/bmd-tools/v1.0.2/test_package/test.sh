#!/bin/sh
# test.sh — bmd-tools smoke test
# Runs bmd-streamer --help and verifies version output is produced.
# bmd-streamer exits with code 1 for --help (unrecognized option),
# but still prints version and usage. We check output, not exit code.
BMD_STREAMER="$1"

if [ -z "$BMD_STREAMER" ]; then
    echo "FAIL: binary path not provided"
    exit 1
fi

if [ ! -f "$BMD_STREAMER" ]; then
    echo "FAIL: binary not found at $BMD_STREAMER"
    exit 1
fi

output=$("$BMD_STREAMER" --help 2>&1)
if echo "$output" | grep -q "bmd-streamer"; then
    echo "PASS: bmd-streamer binary is functional"
    exit 0
else
    echo "FAIL: bmd-streamer did not produce expected output"
    echo "$output" | head -5
    exit 1
fi
