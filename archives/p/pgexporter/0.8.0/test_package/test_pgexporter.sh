#!/bin/sh
# test_pgexporter.sh — Smoke test for pgexporter binary
# Verifies the installed pgexporter binary can run --version
# Usage: ./test_pgexporter.sh /path/to/pgexporter

set -e

BIN_PATH="$1"

if [ -z "$BIN_PATH" ]; then
    echo "FAIL: No binary path provided"
    exit 1
fi

if [ ! -x "$BIN_PATH" ]; then
    echo "FAIL: Binary not found or not executable: $BIN_PATH"
    exit 1
fi

# Run --version and verify output contains version string
OUTPUT=$("$BIN_PATH" --version 2>&1) || true

if echo "$OUTPUT" | grep -q "pgexporter"; then
    echo "PASS: pgexporter binary runs correctly"
    echo "  Output: $OUTPUT"
    exit 0
else
    echo "FAIL: pgexporter --version did not output expected string"
    echo "  Output: $OUTPUT"
    exit 1
fi
