#!/data/service/hnp/bin/bash
# gtkgreet 冒烟：--help 是上游唯一不依赖 greetd daemon 的入口
# （无 socket 时 GTK 窗口路径不可用，故不做登录流程测试）
set -u
BIN="$1"
echo "[test] $BIN --help"
if "$BIN" --help; then
    echo "✅ gtkgreet --help OK"
    exit 0
fi
echo "❌ gtkgreet --help failed"
exit 1
