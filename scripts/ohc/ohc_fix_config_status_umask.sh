#!/bin/sh
# ohc_fix_config_status_umask.sh — fuse-tmp-write-guard SKILL 处理策略②：
# config.status 类脚本内部 umask 重写（补丁模板，oddjob 0.34.7 实证有效）
#
# 用法: ohc_fix_config_status_umask.sh <config.status 路径> [--dry-run]
#
# 背景: autotools 生成的 config.status 在临时目录创建处硬编码
#   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
# 在 FUSE(HMDFS) + uid 映射错位环境（E046 复合陷阱）下，077 umask 建出的
# 0700 目录**创建者自己也写不进**，且 chmod 补救被静默忽略（E046）——
# 唯一有效修复是把脚本内部的 umask 077 改写为 000（外层 wrapper 注入
# umask 000 无效：子 shell 会自我重置，oddjob 实战已验证）。
#
# 行为: 原地改写 `(umask 077 && mktemp` → `(umask 000 && mktemp`，
#       先备份 <path>.umaskbak（若已存在则跳过备份避免覆盖），改写后
#       自校验（grep 确认无残留 077 临时目录模式），幂等（重复运行无害）。
#
# 退出码: 0=已改写或本已合规；2=文件不存在；3=模式未命中（非本陷阱形态，
#         不动文件）；4=改写后自校验失败（已回滚）。

set -u

[ $# -ge 1 ] || { echo "usage: $0 <config.status> [--dry-run]" >&2; exit 64; }

TARGET=$1
DRY_RUN=0
[ "${2:-}" = "--dry-run" ] && DRY_RUN=1

[ -f "$TARGET" ] || { echo "FATAL: not a file: $TARGET" >&2; exit 2; }

# 幂等：已无 077 临时目录模式即视为合规
if ! grep -q 'umask 077 && mktemp' "$TARGET"; then
    echo "[fix-config-status-umask] already clean (no 'umask 077 && mktemp' pattern): $TARGET"
    exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo "[fix-config-status-umask] dry-run: would rewrite 'umask 077 && mktemp' -> 'umask 000 && mktemp' in $TARGET"
    grep -n 'umask 077 && mktemp' "$TARGET"
    exit 0
fi

BAK="$TARGET.umaskbak"
[ -f "$BAK" ] || cp "$TARGET" "$BAK" || exit 4

# 仅替换临时目录创建处的 umask（模式足够特异，不会误伤其他 umask 用途）
sed 's/umask 077 \&\& mktemp/umask 000 \&\& mktemp/g' "$TARGET" > "$TARGET.fixed" || exit 4

# 自校验：改写后不得再有 'umask 077 && mktemp'，且必须出现 'umask 000 && mktemp'
if grep -q 'umask 077 && mktemp' "$TARGET.fixed" || \
   ! grep -q 'umask 000 && mktemp' "$TARGET.fixed"; then
    echo "[fix-config-status-umask] self-check failed, rolling back" >&2
    rm -f "$TARGET.fixed"
    exit 4
fi

mv "$TARGET.fixed" "$TARGET"
echo "[fix-config-status-umask] patched: $TARGET (backup: $BAK)"
exit 0
