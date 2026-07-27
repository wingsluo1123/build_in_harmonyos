#!/usr/bin/env bash
# test_package/test_gnu_typist.sh — smoke test for gnu-typist CLI
set -euo pipefail

echo "[test] gtypist --version"
gtypist --version 2>&1 && echo "✅ gtypist --version OK" || {
    echo "❌ gtypist --version failed"
    exit 1
}

echo "[test] gnu-typist smoke test: PASS"
