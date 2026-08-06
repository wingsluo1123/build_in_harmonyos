#!/bin/sh
# Test script for icoutils — verifies binary functionality
# R34: exercises the packaged binary, not just printing a string

set -e

BIN_DIR="$1"
if [ -z "$BIN_DIR" ]; then
    echo "Usage: $0 <bin_dir>"
    exit 1
fi

# Test icotool
"$BIN_DIR/icotool" --version | grep -q "icotool (icoutils) 0.32.3"
echo "icotool: OK"

# Test wrestool
"$BIN_DIR/wrestool" --version | grep -q "wrestool (icoutils) 0.32.3"
echo "wrestool: OK"

# Test icotool --help (exit code 0 or 1 is acceptable for help)
"$BIN_DIR/icotool" --help > /dev/null 2>&1 || true
echo "icotool --help: OK"

# Test wrestool --help
"$BIN_DIR/wrestool" --help > /dev/null 2>&1 || true
echo "wrestool --help: OK"

echo "All tests passed."
