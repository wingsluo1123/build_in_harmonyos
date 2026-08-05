#!/bin/sh
# test_package/test.sh — smoke test for abuild
# Verifies that the abuild binary is present and responds to --version
set -euo pipefail

echo "[test] abuild --version"
abuild --version 2>&1 || {
    echo "❌ abuild --version failed"
    exit 1
}
echo "✅ abuild --version OK"

echo "[test] abuild --help"
abuild --help 2>&1 | head -5 || {
    echo "❌ abuild --help failed"
    exit 1
}
echo "✅ abuild --help OK (shows usage)"