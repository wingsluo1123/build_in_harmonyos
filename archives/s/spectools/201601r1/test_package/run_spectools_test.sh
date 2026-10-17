#!/bin/sh
# run_spectools_test.sh — spectools 消费者冒烟测试（R34/PF3 口径：真实执行安装产物）
#
# 用法: run_spectools_test.sh <spectool_raw> <spectool_curses> <spectool_net>
#
# 判据（libnfc-tools run_nfc_tools_test.sh 范式）：
#   - exit 126/127      → FAIL（动态库加载失败 / 找不到解释器）
#   - 内容断言不成立    → FAIL（见下）
#
# 测试点（全部离线，无需 Wi-Spy USB 硬件；spectool_raw 在解析参数前先做
# 一次 USB 设备扫描，无硬件时 ndev=0，-h 仍打印用法并 exit 0）：
#   1. spectool_raw -h      参数解析 + 用法横幅（期望 exit 0 + 横幅首行）
#   2. spectool_raw -l      设备枚举（无硬件：期望 "No spectool devices found"
#                           + exit 1；有硬件：期望 "Found N devices" + exit 0）
#   3. spectool_curses -h   参数解析 + 用法横幅
#   4. spectool_net -h      参数解析 + 用法横幅
#
# ── 2026-10-15 修（本次提交的唯一改动）────────────────────────────────────
# 旧版第 1/3/4 点的内容判据是 `grep -qi "usage"` 落在 WARN 分支里。实测
# （qemu-aarch64 + /opt/ohos-guest + libfdchkshim，见 PR 评论的取证）上游
# spectools 的用法输出里**根本没有 "usage" 这个词**：
#   spectool_raw -h  → "spectool_raw [ options ]\n -n / --net ..."（rc=0）
#   spectool_net -h  → "spectool_net [-b <secs>] [-p <port>] [-a <bind address>]"
# 因此该判据**恒不命中** ⇒ 这 3 点永远只打印 WARN，除 126/127 的装载闸门外
# 不会失败，属「永不失败的断言」。现改为命中上游 usage() 的**编译期常量横幅**
# 并升为 FAIL 分支，断言从此可被真实触发（失败时打印实际输出头部便于定位）。
# ─────────────────────────────────────────────────────────────────────────
set -eu

RAW="$1"
CURSES="$2"
NET="$3"
[ -f "$RAW" ] || { echo "FAIL: spectool_raw not found at $RAW"; exit 1; }
[ -f "$CURSES" ] || { echo "FAIL: spectool_curses not found at $CURSES"; exit 1; }
[ -f "$NET" ] || { echo "FAIL: spectool_net not found at $NET"; exit 1; }

fail() { echo "FAIL: $*"; exit 1; }
head2() { printf '%s\n' "$1" | head -2 | tr '\n' '|'; }

echo "[1/4] spectool_raw -h"
# 先单独捕获真实 rc 再比对内容（管道 $? 是 grep 的，且 126/127 的
# shell 错误消息含脚本路径会掩盖真实状态，必须先过 rc 闸门）
H_RC=0
H_OUT=$("$RAW" -h </dev/null 2>&1) || H_RC=$?
if [ "$H_RC" = "126" ] || [ "$H_RC" = "127" ]; then
    fail "spectool_raw -h load error (rc=$H_RC)"
fi
# 上游 spectool_raw.c 的 Usage() 首行是编译期常量 "spectool_raw [ options ]"
if [ "$H_RC" = "0" ] && printf '%s\n' "$H_OUT" | grep -q 'spectool_raw \[ options \]'; then
    echo "  ok: -h prints the 'spectool_raw [ options ]' usage banner and exits 0"
else
    fail "spectool_raw -h rc=$H_RC but usage banner missing (head: $(head2 "$H_OUT"))"
fi

echo "[2/4] spectool_raw -l (device list, no hardware expected)"
L_RC=0
L_OUT=$("$RAW" -l </dev/null 2>&1) || L_RC=$?
if [ "$L_RC" = "126" ] || [ "$L_RC" = "127" ]; then
    fail "spectool_raw -l load error (rc=$L_RC)"
fi
if printf '%s\n' "$L_OUT" | grep -q "No spectool devices found"; then
    echo "  ok: -l reports no devices gracefully (rc=$L_RC)"
elif printf '%s\n' "$L_OUT" | grep -q "Found [1-9]" && [ "$L_RC" = "0" ]; then
    echo "  ok: -l found devices (rc=0)"
else
    fail "spectool_raw -l rc=$L_RC: neither no-device nor found-device output (head: $(head2 "$L_OUT"))"
fi

echo "[3/4] spectool_curses -h"
C_RC=0
C_OUT=$("$CURSES" -h </dev/null 2>&1) || C_RC=$?
if [ "$C_RC" = "126" ] || [ "$C_RC" = "127" ]; then
    fail "spectool_curses -h load error (rc=$C_RC)"
fi
# 上游 spectool_curses.c 的 Usage() 首行是编译期常量 "spectool_curses [ options ]"
if [ "$C_RC" = "0" ] && printf '%s\n' "$C_OUT" | grep -q 'spectool_curses \[ options \]'; then
    echo "  ok: -h prints the 'spectool_curses [ options ]' usage banner and exits 0"
else
    fail "spectool_curses -h rc=$C_RC but usage banner missing (head: $(head2 "$C_OUT"))"
fi

echo "[4/4] spectool_net -h"
N_RC=0
N_OUT=$("$NET" -h </dev/null 2>&1) || N_RC=$?
if [ "$N_RC" = "126" ] || [ "$N_RC" = "127" ]; then
    fail "spectool_net -h load error (rc=$N_RC)"
fi
# 上游 spectool_net 的用法是内联 printf 的编译期常量，首行形如
# "spectool_net [-b <secs>] [-p <port>] [-a <bind address>]"；实测该入口
# rc=255（上游自身 exit(-1) 的既有行为），故此处只断言横幅、不把 rc 作为判据。
if printf '%s\n' "$N_OUT" | grep -q 'spectool_net \[-b'; then
    echo "  ok: -h prints the 'spectool_net [-b ...]' usage banner (rc=$N_RC, upstream exit(-1) semantics)"
else
    fail "spectool_net -h usage banner missing (rc=$N_RC, head: $(head2 "$N_OUT"))"
fi

echo "smoke test done"
exit 0
