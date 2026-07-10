#!/usr/bin/env bash
# test_package/test.sh — smoke test for bazel-diff CLI
set -euo pipefail

echo "[test] bazel-diff --help"
bazel-diff --help && echo "✅ bazel-diff --help OK" || {
    echo "❌ bazel-diff --help failed"
    exit 1
}

echo "[test] bazel-diff --version"
bazel-diff --version 2>/dev/null && echo "✅ bazel-diff --version OK" || {
    echo "⚠ bazel-diff --version not supported (non-fatal)"
}

echo "[test] bazel-diff smoke test: PASS"