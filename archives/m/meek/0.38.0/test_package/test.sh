#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for meek-client and meek-server (R34).
# Runs in conanrun env (PATH includes installed bin/).
#
# meek-client/meek-server require TOR_PT_MANAGED_TRANSPORT_VER env var.
# Without it, they print "ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER" to
# stderr (per Tor PT spec / goptlib) and exit with code 1.
# This test captures stderr (2>&1) to verify that behavior.
set -euo pipefail

echo "[test] meek-client: verify ENV-ERROR output (expected exit 1)"
output=$(meek-client 2>&1) || true
echo "$output" | grep -q "ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER" || {
    echo "❌ meek-client did not output expected ENV-ERROR"
    exit 1
}
echo "✅ meek-client OK"

echo "[test] meek-server: verify ENV-ERROR output (expected exit 1)"
output=$(meek-server 2>&1) || true
echo "$output" | grep -q "ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER" || {
    echo "❌ meek-server did not output expected ENV-ERROR"
    exit 1
}
echo "✅ meek-server OK"

echo "PASS: meek binaries functional"
