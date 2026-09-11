#!/usr/bin/env bash
# test_package/test.sh — nsnake 3.0.1.1 冒烟 + 打包完整性核对
# 用法: bash test.sh [package_folder]   （不给参数时依赖 PATH 上的 nsnake）
set -euo pipefail

PKG="${1:-}"
BIN="${PKG:+$PKG/bin/nsnake}"
BIN="${BIN:-nsnake}"

"$BIN" --version | grep -q 'nsnake v'
echo "[ok] nsnake --version"

if [ -n "$PKG" ]; then
    levels=$(find "$PKG/share/games/nsnake/levels" -name '*.nsnake' 2>/dev/null | wc -l)
    [ "$levels" -eq 31 ] || { echo "[fail] 关卡数 $levels != 31"; exit 1; }
    echo "[ok] 31 个关卡已入包"

    for f in share/man/man6/nsnake.6 share/pixmaps/nsnake.xpm \
             share/applications/nsnake.desktop \
             share/icons/hicolor/16x16/apps/nsnake.png \
             share/icons/hicolor/32x32/apps/nsnake.png; do
        [ -s "$PKG/$f" ] || { echo "[fail] 缺数据文件或为空: $f"; exit 1; }
    done
    echo "[ok] man6 / pixmaps / desktop / icons 均已入包且非空"

    ! grep -qE '\b(VERSION|DATE)\b' "$PKG/share/man/man6/nsnake.6"
    echo "[ok] man6 占位符已替换"
fi

echo "[ok] nsnake smoke + packaging test passed"
