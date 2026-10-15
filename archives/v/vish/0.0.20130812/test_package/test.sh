#!/bin/sh
# test_package/test.sh — smoke test for the vish CLI executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# Two OHOS-specific checks (upstream vish has no test suite, audited in
# MANIFEST.yml):
#   1. vish --version  -> exit 0, stdout contains "0.0.20130812"
#   2. vish --scan     -> exit 0 (real VISA path: viOpenDefaultRM ->
#                         viFindRsrc -> viClose; librevisa portable core
#                         reports 0 devices with no hardware, exits 0)
set -euo pipefail

echo "[test] vish --version (print version, exit 0)"
VERSION_OUT="$(vish --version)"
echo "$VERSION_OUT"
if ! echo "$VERSION_OUT" | grep -q "0.0.20130812"; then
    echo "❌ vish --version did not contain 0.0.20130812"
    exit 1
fi
echo "✅ vish --version passed"

echo "[test] vish --scan (real VISA resource-manager path, exit 0)"
if ! vish --scan >/dev/null 2>&1; then
    echo "❌ vish --scan did not exit 0"
    exit 1
fi
echo "✅ vish --scan passed"
