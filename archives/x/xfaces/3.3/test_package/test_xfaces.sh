#!/bin/sh
# L1 smoke test — xfaces 3.3 (POSIX sh, xidle/myman 同款)
# 用法: test_xfaces.sh <xfaces-binary> <LD_PRELOAD-colon-list>
# 真实执行被测二进制（R34）：无效 DISPLAY 下 XtInitialize 打印
# "Can't open display" 后退出；先决条件是全部 X11 共享库符号解析成功。
set -u

BIN="$1"
PRELOAD="$2"

if [ ! -x "$BIN" ]; then
    echo "FAIL: xfaces binary not executable: $BIN"
    exit 1
fi

OUT=$(DISPLAY=:99-xfaces-smoke-invalid LD_PRELOAD="$PRELOAD" "$BIN" 2>&1)
RC=$?

# 1) 二进制必须能被加载执行（排除 127=not found / 签名拒绝 / 缺符号）
if [ "$RC" -eq 127 ] || echo "$OUT" | grep -qiE "not found|not executable|Permission denied|symbol lookup"; then
    echo "FAIL: xfaces failed to execute (rc=$RC): $OUT"
    exit 1
fi

# 2) X11 初始化错误必须出现（证明 Xt/Xaw/Xmu/Xpm/X11 链接解析完整）
if ! echo "$OUT" | grep -qi "display"; then
    echo "FAIL: expected X11 display error, rc=$RC, output: $OUT"
    exit 1
fi

echo "PASS: xfaces executed, dynamic linking OK, X11 init error as expected (rc=$RC): $OUT"
exit 0
