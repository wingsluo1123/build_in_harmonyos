#!/bin/sh
# test_package/test.sh — smoke test for blender headless executable
# Verifies that the OHOS headless build can initialize without GUI and
# does not crash with missing-library errors (broken dynamic linking).
set -eu

echo "[test] blender --version"
blender --version || {
    echo "❌ blender --version failed"
    exit 1
}
echo "✅ blender --version OK"

echo "[test] blender --help"
blender --help > /dev/null 2>&1 || {
    echo "❌ blender --help failed"
    exit 1
}
echo "✅ blender --help OK"

echo "[test] blender -b --factory-startup (headless init, non-zero exit expected)"
# Factory startup without arguments exits non-zero (expected); crash
# signals (>=128, e.g. SIGSEGV/SIGABRT) or missing shared libraries
# (127) indicate a broken package and must fail the test.
set +e
blender -b --factory-startup > /dev/null 2>&1
rc=$?
set -e
if [ "$rc" -ge 128 ] || [ "$rc" -eq 127 ] || [ "$rc" -eq 126 ]; then
    echo "❌ blender -b --factory-startup crashed (exit code $rc)"
    exit 1
fi
echo "✅ blender -b --factory-startup exited with code $rc (no crash)"
