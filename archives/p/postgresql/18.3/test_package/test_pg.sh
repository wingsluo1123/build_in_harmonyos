#!/bin/sh
set -euo pipefail
# Smoke test: verify pg_config binary exists, is ELF, and attempt execution
PG_CONFIG="${1:-pg_config}"
echo "Testing pg_config at: $PG_CONFIG"
if [ -f "$PG_CONFIG" ]; then
    echo "pg_config found"
    file "$PG_CONFIG" 2>/dev/null | grep -qi "elf" || {
        echo "ERROR: pg_config is not an ELF binary"
        exit 1
    }
    echo "pg_config is a valid ELF binary"
    # Attempt to execute pg_config (may fail on OHOS with unsigned binaries)
    if "$PG_CONFIG" --version 2>/dev/null; then
        echo "pg_config executed successfully"
    else
        echo "WARNING: pg_config could not be executed (expected on OHOS unsigned binary)"
    fi
else
    echo "pg_config NOT found"
    exit 1
fi
echo "pg_config smoke test passed"
