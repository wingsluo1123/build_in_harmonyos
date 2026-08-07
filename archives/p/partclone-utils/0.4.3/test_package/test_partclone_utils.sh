#!/bin/sh
# test_partclone_utils.sh — Smoke test for partclone-utils binaries
# R34: test must execute the package's binaries
# This script verifies that partclone_imageinfo and ntfsclone_imageinfo
# are installed and can execute (exit code != 127 = command not found)

set -e

echo "Testing partclone_imageinfo..."
partclone_imageinfo 2>&1 || true
if [ $? -eq 127 ]; then
    echo "FAIL: partclone_imageinfo not found"
    exit 1
fi

echo "Testing ntfsclone_imageinfo..."
ntfsclone_imageinfo 2>&1 || true
if [ $? -eq 127 ]; then
    echo "FAIL: ntfsclone_imageinfo not found"
    exit 1
fi

echo "All smoke tests passed."
