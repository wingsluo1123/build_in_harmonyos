#!/usr/bin/env bash
# test_package/test.sh — smoke test for man-db executable
set -eu

echo "[test] man --version"
man --version || { echo "❌ man --version failed"; exit 1; }
echo "✅ man --version OK"

echo "[test] mandb --version"
mandb --version || { echo "❌ mandb --version failed"; exit 1; }
echo "✅ mandb --version OK"

echo "[test] whatis --version"
whatis --version || { echo "❌ whatis --version failed"; exit 1; }
echo "✅ whatis --version OK"

echo "[test] lexgrog --version"
lexgrog --version || { echo "❌ lexgrog --version failed"; exit 1; }
echo "✅ lexgrog --version OK"
