#!/bin/sh
# Test fdupes binary
FDUPES_BIN="$1"
if [ -z "$FDUPES_BIN" ]; then
    echo "Usage: $0 <fdupes_binary>"
    exit 1
fi
"$FDUPES_BIN" --version 2>&1 | grep -q "fdupes 2.4.0" || exit 1
echo "fdupes version check: PASS"
exit 0
