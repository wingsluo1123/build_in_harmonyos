#!/bin/sh
# test_version.sh — Verify incus client binary reports correct version
# This test runs "incus version" and checks the output contains "7.1"
set -e

OUTPUT=$(incus version 2>&1)
echo "$OUTPUT" | grep -q "7.1" && echo "PASS: incus version reports 7.1" || {
    echo "FAIL: incus version does not report expected version"
    echo "Output: $OUTPUT"
    exit 1
}
