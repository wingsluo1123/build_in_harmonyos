#!/bin/sh
# test_package/test.sh — kolf 26.04.0 冒烟测试
# 用法: test.sh <kolf 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
# 每个通过的检查打印一行 `SMOKE-PASS <名称>`（HMBS 标记的确定性计数源）。
set -eu

GUI="$1"

echo "[test] binary: $GUI"
test -x "$GUI" || { echo "[test] FAIL kolf not executable"; exit 1; }
echo "SMOKE-PASS binary-exists"

# ---------- 断言 2: kolf --version ----------
# KAboutData::setupCommandLine 在 GUI 主窗口创建前处理 --version
echo "[test] $GUI --version"
OUT="$("$GUI" --version 2>&1)" || {
    echo "[test] FAIL --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *26.04.0*)
        echo "[test] PASS --version reports 26.04.0"
        ;;
    *)
        echo "[test] FAIL unexpected version output"
        exit 1
        ;;
esac
echo "SMOKE-PASS version-string"

# ---------- 断言 3: kolf --help ----------
echo "[test] $GUI --help"
HELP="$("$GUI" --help 2>&1)" || {
    echo "[test] FAIL --help exited non-zero"
    echo "$HELP"
    exit 1
}
test -n "$HELP" || { echo "[test] FAIL --help produced empty output"; exit 1; }
echo "SMOKE-PASS help-output"

# ---------- 断言 4: kolf --license ----------
echo "[test] $GUI --license"
LIC="$("$GUI" --license 2>&1)" || {
    echo "[test] FAIL --license exited non-zero"
    echo "$LIC"
    exit 1
}
test -n "$LIC" || { echo "[test] FAIL --license produced empty output"; exit 1; }
echo "SMOKE-PASS license-output"

echo "[test] ALL SMOKE ASSERTIONS PASSED (4 checks)"
