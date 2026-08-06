#!/data/service/hnp/bin/bash
set -euo pipefail

HAPROXY_BIN="${1:-haproxy}"
TEST_CFG="${2:-test_config.cfg}"

echo "[step] haproxy -vv"
"$HAPROXY_BIN" -vv

echo "[step] haproxy -c -f $TEST_CFG"
"$HAPROXY_BIN" -c -f "$TEST_CFG"

echo "[ok] all tests passed"
