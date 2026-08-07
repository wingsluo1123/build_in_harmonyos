#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nnn executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] nnn -V (version)"
nnn -V && echo "✅ version OK" || {
    echo "❌ nnn -V failed"
    exit 1
}

echo "[test] nnn -h (help)"
nnn -h > /dev/null 2>&1 && echo "✅ help OK" || {
    echo "❌ nnn -h failed"
    exit 1
}

echo "✅ All tests passed"
