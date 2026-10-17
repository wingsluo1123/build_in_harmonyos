#!/usr/bin/env bash
# detect-gnome-yelp-itstool.sh — 识别「OHOS 上 itstool 不可用 → gnome.yelp 帮助页
# 构建失败」这一共性阻塞问题。
#
# 用法:
#   detect-gnome-yelp-itstool.sh <源码目录> [构建日志文件]
#
# 判定（源码侧 + 环境侧两条同时满足即命中；日志侧可选作交叉佐证）:
#   A 源码侧: meson.build 里存在 gnome.yelp( 调用，或 subdir('help') 指向的
#             help/meson.build 使用 gnome.yelp(  —— 即构建会调用 itstool 合并
#             帮助页翻译。
#   B 环境侧: itstool 在 OHOS 构建环境里「不可用」——未找到，或找到但执行
#             退出码非 0（shebang 指向的解释器缺失 / Exec format error /
#             python 的 libxml2 绑定缺失）。
#   C 日志侧: 构建日志命中 itstool 崩溃特征（可选，提供时作交叉佐证）。
#
# 命中 → 打印命中项与处理策略，退出码 1；未命中 → 退出码 0。
#
# 不写死任何本地绝对路径：源码目录由参数给出，itstool 由 PATH 解析。

set -euo pipefail
# 安全模式（code-style#7）。本脚本以显式退出码表达判定结果（命中 1 / 未命中 0），
# 因此所有「未命中属于正常」的查询（grep / command -v / itstool --version）均已用
# `|| true` 或 `|| VAR=$?` 显式容错，不会被 -e 提前中断。

SRC="${1:-}"
LOG="${2:-}"
HIT_SRC=0
HIT_ENV=0
HIT_LOG=0

if [ -z "$SRC" ]; then
    echo "usage: $0 <source-dir> [build-log]" >&2
    exit 2
fi
if [ ! -d "$SRC" ]; then
    echo "FAIL: source dir not found: $SRC" >&2
    exit 2
fi

# ---------------------------------------------------------------- A 源码侧
# -m 限定每个文件的命中数，避免长输出；不用管道 head（SIGPIPE）
YELP_HITS=$(grep -rn -m 5 "gnome\.yelp(" "$SRC" \
    --include="meson.build" --include="*.build" 2>/dev/null || true)
if [ -n "$YELP_HITS" ]; then
    HIT_SRC=1
fi

# subdir('help') 也算命中（帮助页目录被无条件纳入构建）
HELP_SUBDIR=$(grep -rn -m 5 "subdir('help')\|subdir(\"help\")" "$SRC" \
    --include="meson.build" 2>/dev/null || true)
if [ -n "$HELP_SUBDIR" ]; then
    HIT_SRC=1
fi

# ---------------------------------------------------------------- B 环境侧
ITSTOOL_PATH=$(command -v itstool 2>/dev/null || true)
ITSTOOL_VERDICT="not-found"
ITSTOOL_DETAIL=""
ITSTOOL_RC=0
if [ -n "$ITSTOOL_PATH" ]; then
    ITSTOOL_RC=0
    "$ITSTOOL_PATH" --version >/dev/null 2>&1 || ITSTOOL_RC=$?
    if [ "$ITSTOOL_RC" -ne 0 ]; then
        ITSTOOL_VERDICT="present-but-unusable"
        ITSTOOL_DETAIL="exit code $ITSTOOL_RC"
        # shebang 指向的解释器是否存在（OHOS 上常见：指向构建机不存在的 python）
        SHEBANG=$(head -1 "$ITSTOOL_PATH" 2>/dev/null | sed 's/^#!//' | awk '{print $1}' || true)
        if [ -n "$SHEBANG" ] && [ ! -e "$SHEBANG" ]; then
            ITSTOOL_DETAIL="$ITSTOOL_DETAIL; shebang interpreter missing: $SHEBANG"
        fi
    else
        ITSTOOL_VERDICT="usable"
    fi
else
    ITSTOOL_VERDICT="not-found"
fi
if [ "$ITSTOOL_VERDICT" != "usable" ]; then
    HIT_ENV=1
fi

# ---------------------------------------------------------------- C 日志侧
if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    if grep -qE "code=126|Program 'itstool' not found|itstool.*(Exec format error|Permission denied|No module named|not executable)|gnome\.yelp" "$LOG" 2>/dev/null; then
        HIT_LOG=1
    fi
fi

# ---------------------------------------------------------------- 输出
echo "== detect: gnome.yelp / itstool unusable on OHOS =="
echo "source dir          : $SRC"
echo "[A] gnome.yelp( in source : $HIT_SRC"
if [ -n "$YELP_HITS" ]; then
    echo "$YELP_HITS" | sed 's/^/      /'
fi
if [ -n "$HELP_SUBDIR" ]; then
    echo "$HELP_SUBDIR" | sed 's/^/      /'
fi
echo "[B] itstool verdict  : $ITSTOOL_VERDICT ${ITSTOOL_DETAIL:+($ITSTOOL_DETAIL)}"
echo "      itstool path    : ${ITSTOOL_PATH:-<not on PATH>}"
if [ -n "$LOG" ]; then
    echo "[C] build log \"$LOG\" matches: $HIT_LOG"
fi

if [ "$HIT_SRC" -eq 1 ] && [ "$HIT_ENV" -eq 1 ]; then
    echo
    echo "HIT: 构建会调用 gnome.yelp() 合并帮助页翻译，而本环境 itstool 不可用。"
    echo "     处理策略: 用补丁在 meson_options.txt 增加布尔选项 help（默认 false），"
    echo "              并在 meson.build 用 if get_option('help') 守卫 subdir('help')，"
    echo "              使 help 目录默认不进构建（详见同目录 strategy.md）。"
    if [ "$HIT_LOG" -eq 1 ]; then
        echo "     日志侧已交叉确认 itstool 崩溃特征。"
    fi
    exit 1
fi

if [ "$HIT_LOG" -eq 1 ]; then
    echo
    echo "HIT: 构建日志命中 itstool 崩溃特征（源码/环境判定未同时满足，请人工复核）。"
    exit 1
fi

echo
echo "no hit: 源码未使用 gnome.yelp()，或本环境 itstool 可用。"
exit 0
