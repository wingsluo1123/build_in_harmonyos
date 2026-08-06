#!/bin/sh
# Smoke test for mokutil — verify the binary runs and prints version
set -e

BIN_DIR="$1"
MOKUTIL="${BIN_DIR}/mokutil"

# Verify the binary exists
if [ ! -x "$MOKUTIL" ]; then
    echo "ERROR: mokutil binary not found at $MOKUTIL"
    exit 1
fi

# Run mokutil --version (R34: exercise the packaged artifact)
VERSION=$("$MOKUTIL" --version 2>&1)
echo "mokutil version: $VERSION"

# Verify version output is non-empty
if [ -z "$VERSION" ]; then
    echo "ERROR: mokutil --version produced no output"
    exit 1
fi

echo "mokutil: smoke test passed"
