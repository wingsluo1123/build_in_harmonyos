#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bcal executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] bcal -h (version check)"
bcal -h | grep -q "Version 2.5" && echo "✅ bcal -h version OK" || {
    echo "❌ bcal -h failed to show version"
    exit 1
}

echo "[test] bcal -c 255 (radix conversion)"
bcal -c 255 | grep -q "11111111" && echo "✅ bcal -c 255 radix OK" || {
    echo "❌ bcal -c 255 radix conversion failed"
    exit 1
}

echo "[test] bcal -m 1 kib (byte calculation)"
bcal -m 1 kib | grep -q "1024" && echo "✅ bcal -m 1 kib byte calc OK" || {
    echo "❌ bcal -m 1 kib byte calculation failed"
    exit 1
}
