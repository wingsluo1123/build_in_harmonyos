#!/bin/sh
set -euo pipefail
# Smoke test: verify pg_config binary exists and is a valid ELF binary
# OHOS: unsigned ELF binaries cannot be executed in CI, so we verify
# file existence and type instead of running the binary
PG_CONFIG="${1:-pg_config}"
echo "Testing pg_config at: $PG_CONFIG"
if [ -f "$PG_CONFIG" ]; then
    echo "pg_config found"
    file "$PG_CONFIG" 2>/dev/null | grep -qi "elf" || {
        echo "ERROR: pg_config is not an ELF binary"
        exit 1
    }
    echo "pg_config is a valid ELF binary"
else
    echo "pg_config NOT found"
    exit 1
fi
echo "pg_config smoke test passed"
