#!/usr/bin/env bash
# test_package/test.sh — smoke test for ruby-build CLI
set -euo pipefail

# Find bash directory
BASH_DIR="$(dirname "$(command -v bash 2>/dev/null || echo /usr/local/bin/bash)")"

echo "[test] ruby-build --version"
ruby-build --version && echo "✅ ruby-build --version OK" || {
    echo "❌ ruby-build --version failed"
    exit 1
}

echo "[test] ruby-build --list (first 5 entries)"
LIST_OUTPUT=$(ruby-build --list 2>&1 | head -5)
echo "$LIST_OUTPUT"
if [ -n "$LIST_OUTPUT" ]; then
    echo "✅ ruby-build --list OK"
else
    echo "❌ ruby-build --list returned empty"
    exit 1
fi

echo "[test] ruby-build smoke test: PASS"
