#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nmap executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] nmap --version"
nmap --version && echo "✅ nmap --version OK" || {
    echo "❌ nmap --version failed"
    exit 1
}

echo "[test] ncat --version"
ncat --version && echo "✅ ncat --version OK" || {
    echo "❌ ncat --version failed"
    exit 1
}

echo "[test] nping --version"
nping --version && echo "✅ nping --version OK" || {
    echo "❌ nping --version failed"
    exit 1
}

echo "All tests passed!"
