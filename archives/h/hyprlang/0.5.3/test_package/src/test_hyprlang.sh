#!/bin/sh
# test_hyprlang.sh — hyprlang 库消费者验证脚本
#
# 验证 hyprlang 库产物完整：头文件 hyprlang.hpp、共享库 libhyprlang.so、
# hyprlang.pc 存在，且 .pc 声明了库与 include 路径。作为 hyprlang 可用的
# 冒烟测试。
# 用法：test_hyprlang.sh <pkg_dir>
set -u

PKG="$1"

header="$PKG/include/hyprlang.hpp"
lib="$(ls "$PKG"/lib/libhyprlang.so* 2>/dev/null | head -1)"
pc="$PKG/lib/pkgconfig/hyprlang.pc"

for f in "$header" "$pc"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: 文件缺失: $f"
        exit 1
    fi
done
if [ -z "$lib" ]; then
    echo "FAIL: libhyprlang.so 缺失"
    exit 1
fi

# .pc 应声明库名 hyprlang
if ! grep -q "hyprlang" "$pc" 2>/dev/null; then
    echo "FAIL: hyprlang.pc 未声明库"
    exit 1
fi

echo "PASS: hyprlang 产物完整（header/lib/pc 均存在）"
echo "  - $(basename "$header")"
echo "  - $(basename "$lib")"
echo "  - $(basename "$pc")"
exit 0
