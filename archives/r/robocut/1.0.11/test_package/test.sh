#!/usr/bin/env bash
# test_package/test.sh — robocut 1.0.11 消费者冒烟测试（鸿蒙特有测试，R34）
# 在 conanrun 环境下实跑被测包安装的 bin/robocut：
#   A1 二进制在 PATH 中
#   A2 `robocut --version` rc=0 且输出含上游版本号 1.0.11
#   A3 `robocut --help`    rc=0 且输出含 "Usage:"
# --version/--help 在 main.cpp 的 QApplication 之前处理，无需显示设备。
set -uo pipefail

export QT_QPA_PLATFORM=offscreen

fail=0
say() { printf '%s\n' "$*"; }

# --- A1: 二进制可达 ---
if command -v robocut >/dev/null 2>&1; then
    say "A1 PASS: robocut found in PATH ($(command -v robocut))"
else
    say "A1 FAIL: robocut not found in PATH"
    exit 1
fi

# --- A2: --version ---
ver_out="$(robocut --version 2>&1)"
ver_rc=$?
say "--- robocut --version (rc=$ver_rc) ---"
say "$ver_out"
if [ "$ver_rc" -eq 0 ] && printf '%s' "$ver_out" | grep -q '1\.0\.11'; then
    say "A2 PASS: --version rc=0 and reports 1.0.11"
else
    say "A2 FAIL: --version rc=$ver_rc output does not report 1.0.11"
    fail=1
fi

# --- A3: --help ---
help_out="$(robocut --help 2>&1)"
help_rc=$?
say "--- robocut --help (rc=$help_rc) ---"
say "$help_out"
if [ "$help_rc" -eq 0 ] && printf '%s' "$help_out" | grep -q 'Usage:'; then
    say "A3 PASS: --help rc=0 and prints Usage"
else
    say "A3 FAIL: --help rc=$help_rc does not print Usage"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    say "PASS: robocut 1.0.11 consumer smoke test (3/3 assertions)"
    exit 0
fi
say "FAIL: robocut 1.0.11 consumer smoke test"
exit 1
