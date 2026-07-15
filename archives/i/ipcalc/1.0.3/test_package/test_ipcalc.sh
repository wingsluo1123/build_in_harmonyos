#!/usr/bin/zsh
# test_ipcalc.sh — Smoke test for ipcalc binary
# Verifies basic IPv4 and IPv6 calculations work correctly.

set -euo pipefail

IPCALC="${1:-ipcalc}"

# Test 1: Version
"$IPCALC" --version

# Test 2: IPv4 calculation
OUTPUT=$("$IPCALC" 192.168.1.1/24)
echo "$OUTPUT" | grep -q "192.168.1.0/24" || { echo "FAIL: network not found"; exit 1; }
echo "$OUTPUT" | grep -q "192.168.1.255" || { echo "FAIL: broadcast not found"; exit 1; }
echo "IPv4 test passed"

# Test 3: IPv6 calculation
OUTPUT=$("$IPCALC" 2001:db8::/32)
echo "$OUTPUT" | grep -q "2001:db8::" || { echo "FAIL: IPv6 network not found"; exit 1; }
echo "IPv6 test passed"

echo "All tests passed"
