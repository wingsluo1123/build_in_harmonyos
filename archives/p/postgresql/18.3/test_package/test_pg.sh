#!/bin/sh
# Smoke test: verify pg_config is functional
PG_CONFIG="${1:-pg_config}"
echo "Testing pg_config at: $PG_CONFIG"
"$PG_CONFIG" --version
"$PG_CONFIG" --bindir
"$PG_CONFIG" --libdir
echo "pg_config smoke test passed"
