#!/bin/sh
# ohc_umask_wrap.sh — fuse-tmp-write-guard SKILL 处理策略①：umask 000 环境注入
#
# 用法: ohc_umask_wrap.sh <command> [args...]
#
# 背景: 本仓库工作区挂载在 FUSE(HMDFS) 上，存在复合平台陷阱（E046 具体化）：
#   ① uid 映射错位——进程 uid 与文件显示属主不一致，属主权限不生效；
#   ② chmod 被静默忽略（E046），事后补救无效；
#   ③ 工具链惯例 umask 077 建临时目录 → 0700/0600 → 创建者自己随即写不进
#      （实证: oddjob 0.34.7 config.status 写 subs1.awk 被拒；上游
#        tests/cmdparse harness 的 mktemp 输出文件写入失败致 cmp 空文件）。
#   umask 000 创建的 0777/0666 目录/文件不依赖属主位，任何 uid 均可写——
#   这是该文件系统上唯一可靠的绕法。
#
# 语义: 仅放宽 umask 后执行命令，退出码原样透传；不改写、不拦截任何业务
#       文件；不产生自身输出（调用方自行把 stdout/stderr 重定向到文件，
#       防管道 SIGPIPE——本 SKILL 约束）。
#
# 退出码: 64 = 用法错误；否则 = <command> 的退出码。

if [ $# -eq 0 ]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 64
fi

OLD_UMASK=$(umask)
umask 000
"$@"
rc=$?
umask "$OLD_UMASK"
exit $rc
