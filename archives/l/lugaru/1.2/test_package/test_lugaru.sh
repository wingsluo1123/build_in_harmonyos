#!/bin/sh
# lugaru 1.2 消费者运行时冒烟脚本（test_package 的一部分，L0c 测试源文件）
#
# 在无 GPU / 无 Wayland 合成器的环境下真实执行被测二进制，只走 main.cpp 的
# 选项解析与版本横幅分支（在任何 SDL 初始化之前 return），因此不需要显示设备。
#
# 用法: test_lugaru.sh <workdir> <libdirs> <binary> [args...]
#   workdir  可写工作目录（同时作为 cwd）
#   libdirs  依赖 lib/ 目录列表（冒号分隔），前置到 LD_LIBRARY_PATH
#   binary   被测可执行文件
#   输出: <workdir>/lugaru-<args>.log 与同名 .rc（退出码一行）
set -u

workdir="$1"; shift
libdirs="$1"; shift
exe="$1"; shift

tag=$(printf '%s' "$*" | tr -d '-' | tr ' ' '_')
[ -n "$tag" ] || tag="noargs"
log="$workdir/lugaru-$tag.log"

export LD_LIBRARY_PATH="$libdirs:${LD_LIBRARY_PATH:-}"
cd "$workdir" || exit 90

timeout 60 "$exe" "$@" > "$log" 2>&1
echo $? > "$log.rc"
