#!/bin/sh
set -eu
# Smoke test: verify postgresql-rum extension artifacts
RUM_SO="${1:-rum.so}"
echo "Testing rum extension artifacts"
echo "Checking: $RUM_SO"
if [ -f "$RUM_SO" ]; then
    echo "rum.so found"
    file "$RUM_SO" 2>/dev/null || true
    # R34: Verify shared library exports the PostgreSQL extension entry symbol
    if nm -D "$RUM_SO" 2>/dev/null | grep -q " _PG_init"; then
        echo "rum extension symbol check passed"
    else
        echo "ERROR: _PG_init symbol not found in rum.so"
        exit 1
    fi
else
    echo "rum.so NOT found"
    exit 1
fi
echo "rum extension smoke test passed"
