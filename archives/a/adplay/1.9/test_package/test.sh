#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for adplay CLI player
# Usage: test.sh <package_folder>
set -euo pipefail

PKG_DIR="${1:?usage: test.sh <package_folder>}"

echo "[test] verifying adplay binary at: ${PKG_DIR}"
BIN="${PKG_DIR}/bin/adplay"
if [ ! -x "${BIN}" ]; then
    echo "❌ adplay binary not found: ${BIN}"
    ls -la "${PKG_DIR}/bin/" 2>/dev/null || true
    exit 1
fi

echo "✅ adplay binary exists and is executable"
# --help 是纯命令行参数解析，不依赖音频设备；失败即真实运行时问题（R9 禁止伪造通过）
if "${BIN}" --help > /dev/null 2>&1; then
    echo "✅ adplay --help OK"
else
    echo "❌ adplay --help failed (exit $?) — binary has a real runtime problem"
    exit 1
fi
