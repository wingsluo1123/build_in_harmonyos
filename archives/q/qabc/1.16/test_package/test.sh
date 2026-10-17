#!/data/service/hnp/bin/bash
# qabc test_package 冒烟测试（offscreen 模式，CI 无显示服务器）
set -euo pipefail

BIN="$(command -v qabc)"
[ -n "$BIN" ] || { echo "FAIL: qabc not found in PATH"; exit 1; }
echo "== qabc --version =="
QT_QPA_PLATFORM=offscreen "$BIN" --version 2>&1 | grep -q "QAbc 1.16" \
  && echo "PASS: version string" || { echo "FAIL: version"; exit 1; }
echo "== qabc --help =="
QT_QPA_PLATFORM=offscreen "$BIN" --help 2>&1 | grep -q "ABC music notation" \
  && echo "PASS: help text" || { echo "FAIL: help"; exit 1; }
echo "ALL TESTS PASSED"