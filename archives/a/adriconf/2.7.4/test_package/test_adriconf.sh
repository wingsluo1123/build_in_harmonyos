#!/bin/sh
# test_adriconf.sh — validate the packaged adriconf 2.7.4 binary (R34).
# adriconf 是 GTK4 GUI 应用（Mesa drirc 配置器），test_package 验证安装产物：
#   1) bin/adriconf 存在且为 ELF 可执行文件（magic 校验）
#   2) adriconf --help 真正执行：exec 被拒（未签名/不可执行）必须 fail，
#      仅对"无显示环境非零退出但确有 GTK 帮助输出"宽容（d11amp 先例）
set -euo pipefail

fail() { echo "test FAILED: $1"; exit 1; }

# locate installed binary
ADR_BIN="$(command -v adriconf || which adriconf || echo adriconf)"

if [ ! -f "$ADR_BIN" ]; then
    fail "adriconf binary not found: $ADR_BIN"
fi
echo "ok   : adriconf found at $ADR_BIN"

magic="$(head -c 4 "$ADR_BIN" | od -An -tx1 | tr -d ' \n')"
if [ "$magic" = "7f454c46" ]; then
    echo "ok   : adriconf is ELF (magic verified)"
else
    fail "adriconf is not an ELF binary (magic=$magic)"
fi

echo "=== adriconf --help ==="
# 捕获退出码与输出；不吞错（R9 禁止 || true 掩盖失败）。
set +e
HELP_OUT="$("$ADR_BIN" --help 2>&1)"
RC=$?
set -e

if [ "$RC" -ne 0 ] && [ -z "$HELP_OUT" ]; then
    fail "--help 退出码 $RC 且无任何输出（二进制未真正执行）"
fi
# exec 被拒（未签名/加载失败）时 stderr 含 Operation not permitted /
# Error loading shared library — 一律视为产物不可用
if echo "$HELP_OUT" | grep -qiE "operation not permitted|error loading shared library|cannot execute"; then
    fail "--help 执行被拒: $(echo "$HELP_OUT" | head -1)"
fi
# GUI 应用（GTK4）无显示环境（headless CI）下 --help 会启动 GTK 后报
# "Failed to open display" 而非打印帮助文本：进程已真正执行（R34 实质
# 验证二进制可执行性），GTK 初始化警告即执行证据。判定口径：
#   ok = 退出码 0，或输出含应用名，或输出含 GTK 启动证据（Gtk-WARNING/
#   Gtk-Message/process 行——说明已进入 GTK 初始化）
if [ "$RC" -eq 0 ] || echo "$HELP_OUT" | grep -qi "adriconf" \
    || echo "$HELP_OUT" | grep -qE "Gtk-(WARNING|Message)"; then
    echo "ok   : adriconf 二进制已真实执行 (exit=$RC)"
else
    fail "--help 异常退出且无 GTK 启动证据 (exit=$RC)"
fi

echo "test OK"
exit 0
