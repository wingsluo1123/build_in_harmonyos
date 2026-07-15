#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for whois executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] whois --help"
# whois --help exits with code 1 (non-standard), so check output content
output=$(whois --help 2>&1 || true)
if echo "$output" | grep -q "Usage:"; then
    echo "✅ --help shows usage OK"
else
    echo "❌ whois --help did not show usage"
    exit 1
fi
