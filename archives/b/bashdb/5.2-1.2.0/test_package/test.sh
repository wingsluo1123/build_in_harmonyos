#!/bin/bash
# test_package/test.sh — smoke test for bashdb
set -eu

echo "[test] bashdb --version"
bashdb --version && echo "✅ --version OK" || {
    echo "❌ bashdb --version failed"
    exit 1
}
