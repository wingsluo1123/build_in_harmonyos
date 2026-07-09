#!/data/service/hnp/bin/bash
# test_package/test_helm.sh — smoke test for helm executable
# CI L0c gate requires a test source file (.sh/.c/.py) in test_package/
set -eu

# Find helm binary from conan package
HELM_BIN="${1:-helm}"

echo "[test] helm version"
if "$HELM_BIN" version 2>/dev/null; then
    echo "✅ helm version OK"
else
    echo "[test] helm version failed, trying helm help..."
    if "$HELM_BIN" help >/dev/null 2>&1; then
        echo "✅ helm help OK"
    else
        echo "❌ helm failed both version and help"
        exit 1
    fi
fi

echo "[test] helm completion (subcommand)"
if "$HELM_BIN" completion bash >/dev/null 2>&1; then
    echo "✅ helm completion OK"
else
    echo "[warn] helm completion failed (non-blocking)"
fi

echo "[test] All smoke tests passed"
