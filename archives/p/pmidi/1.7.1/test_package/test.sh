#!/bin/sh
# R34：真实执行被测包安装的 pmidi 可执行文件（消费者视角，非空壳）
set -u
fails=0

# 1) 版本输出（真实运行主程序）
OUT="$(pmidi -v 2>&1)"
echo "pmidi -v -> $OUT"
case "$OUT" in
    *pmidi-1.7.1*) echo "ok   - version string" ;;
    *) echo "FAIL - version string, got: $OUT"; fails=$((fails + 1)) ;;
esac

# 2) 未指定输出端口时的真实行为（主流程给出提示，而非崩溃）
OUT2="$(pmidi 2>&1 || true)"
echo "pmidi (no args) -> $OUT2"
case "$OUT2" in
    *"No client/port specified"*) echo "ok   - no-port guard reached" ;;
    *) echo "FAIL - no-port guard, got: $OUT2"; fails=$((fails + 1)) ;;
esac

# 3) 手册页随包安装
PREFIX="$(dirname "$(dirname "$(command -v pmidi)")")"
if [ -f "$PREFIX/share/man/man1/pmidi.1" ]; then
    echo "ok   - man page installed ($PREFIX/share/man/man1/pmidi.1)"
else
    echo "FAIL - man page missing under $PREFIX/share/man/man1/"
    fails=$((fails + 1))
fi

if [ "$fails" -ne 0 ]; then
    echo "$fails pmidi consumer assertion(s) failed"
    exit 1
fi
echo "all pmidi consumer assertions passed"
