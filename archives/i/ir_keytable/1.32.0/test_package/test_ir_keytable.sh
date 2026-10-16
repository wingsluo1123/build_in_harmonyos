#!/bin/sh
# test_ir_keytable.sh — ir_keytable test_package 测试脚本
# 验证 ir-keytable 可执行 + 实际运行（--version/--help 确定性输出，无需 IR 设备）。
# R34：实质执行被测包二进制（非空壳）。
#
# 用法: sh test_ir_keytable.sh <bin_dir>
set -u

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
IR_KEYTABLE="$BIN_DIR/ir-keytable"

echo "== 0. [PROBE] 鸿蒙 PC 设备能力探测（rule12 实证，只收集信息不影响 pass/fail）=="
echo "[PROBE] date: $(date 2>/dev/null || echo unknown)"
echo "[PROBE] uname: $(uname -a 2>/dev/null || echo unknown)"
echo "[PROBE] id: $(id 2>/dev/null || echo unknown)"
echo "[PROBE] --- /sys/class/rc/ (物理 rc 设备，方案B' 关键) ---"
ls -la /sys/class/rc/ 2>&1 | head -40 || true
RC_COUNT=$(ls /sys/class/rc/ 2>/dev/null | wc -l | tr -d ' ')
echo "[PROBE] /sys/class/rc/ entry count: ${RC_COUNT:-0}"
echo "[PROBE] --- /sys/class/rc/rc*/ (rc 设备 sysfs 详情) ---"
for d in /sys/class/rc/rc*; do
    [ -d "$d" ] || continue
    echo "[PROBE] $d:"
    ls "$d" 2>&1 | head -20 || true
done
echo "[PROBE] --- /dev/uinput (uinput 虚拟设备支持) ---"
if [ -e /dev/uinput ]; then echo "[PROBE] /dev/uinput: EXISTS"; else echo "[PROBE] /dev/uinput: ABSENT"; fi
echo "[PROBE] --- /dev/input/event* (input 设备) ---"
ls -la /dev/input/event* 2>&1 | head -40 || true
echo "[PROBE] === PROBE END ==="

echo "== 1. 可执行性检查 =="
if [ ! -x "$IR_KEYTABLE" ]; then
    echo "FAIL: ir-keytable not executable" >&2
    exit 1
fi
echo "OK: ir-keytable executable found at $IR_KEYTABLE"

echo "== 2. --version 实际运行（argp 标准选项，确定性输出）=="
OUT=$( { "$IR_KEYTABLE" --version 2>&1 || true; } )
if echo "$OUT" | grep -qi "ir-keytable\|version\|v4l-utils"; then
    echo "OK: ir-keytable --version output: $OUT"
else
    echo "FAIL: ir-keytable --version no expected output: $OUT" >&2
    exit 1
fi

echo "== 3. --help 实际运行（用法输出）=="
HELP_OUT=$( { "$IR_KEYTABLE" --help 2>&1 || true; } )
if echo "$HELP_OUT" | grep -qi "usage\|sysdev\|protocol\|keymap\|scancode"; then
    echo "OK: ir-keytable --help produced usage output"
else
    echo "FAIL: ir-keytable --help no expected output: $HELP_OUT" >&2
    exit 1
fi

echo "== ALL TESTS PASSED =="
