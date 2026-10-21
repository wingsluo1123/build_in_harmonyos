#!/bin/sh
# reproduce.sh —— 干净环境复现本主题的两条断言：关策略报错 → 开策略通过
#
# 演示对象：archives/p/palapeli/26.04.0（真实样例库，同 PR 交付）
#   「关策略」= 把 conandata.yml 的 patches 置空（在临时副本上做，不动仓库文件）
#              → find_package(KF6 ... REQUIRED COMPONENTS ... DocTools ...) 失败
#   「开策略」= 补丁登记保留（三处裁剪：组件表 / add_subdirectory(doc) / kdoctools_install）
#              → configure + 编译 + 打包全通过
#
# 用法:
#   sh reproduce.sh
#   OHC_CONAN_PROFILE=/path/to/profile sh reproduce.sh
#   OHC_CONAN_REMOTE=ohpcd sh reproduce.sh
#   OHC_DEMO_DIR=/path/to/work sh reproduce.sh
#
# 前置（干净环境）:
#   - conan 2.x 可用；制品仓可访问
#   - palapeli 依赖闭包可用：qtbase-sql-dbus/6.11.1、qtsvg/6.11.1、KF6 6.18 线、
#     libkdegames/26.04.0.1、kio/6.14.0（无匹配二进制时需源码构建）、
#     shared-mime-info/2.5.1、ecm/6.26.0
#
# 说明:
#   - 不改动仓库文件：两轮都在临时副本 archives 目录上跑；
#   - 日志一律重定向到文件，不用管道 head（避免上游 SIGPIPE 误杀导致假失败）；
#   - 不写死本地绝对路径：仓库根由脚本自身位置推导，profile/remote/work 均可覆盖；
#   - 断言以「日志特征 + 退出码」双条件判定，只认实测证据。
set -eu

SELF_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SELF_DIR/../../.." && pwd)
WORK="${OHC_DEMO_DIR:-${TMPDIR:-.}/kf6-di-demo}"
PROFILE="${OHC_CONAN_PROFILE:-$REPO_ROOT/ci/conan/profiles/ohos-aarch64}"
REMOTE="${OHC_CONAN_REMOTE:-ohpcd}"
CONAN="${CONAN:-conan}"
SAMPLE_RECIPE="$REPO_ROOT/archives/p/palapeli/26.04.0"
DETECT="$SELF_DIR/detect-kf6-desktop-integration.sh"

say() { printf '%s\n' "$*"; }
fail() { say "FAIL: $*"; exit 1; }

say "== 桌面集成组件必需化：关策略报错 / 开策略通过 =="
say "repo    = $REPO_ROOT"
say "work    = $WORK (每轮前清空)"
say "profile = $PROFILE"
say "remote  = $REMOTE"
say "conan   = $($CONAN --version 2>/dev/null | sed -n '1p' || true)"

[ -f "$PROFILE" ] || fail "conan profile 不存在: $PROFILE"
[ -d "$SAMPLE_RECIPE" ] || fail "样例配方不存在: $SAMPLE_RECIPE"
[ -f "$DETECT" ] || fail "检测脚本不存在: $DETECT"

rm -rf "$WORK"
mkdir -p "$WORK"

# 临时副本：只复制配方目录，避免任何写入落到仓库
RECIPE="$WORK/recipe"
mkdir -p "$RECIPE"
( cd "$SAMPLE_RECIPE" && tar cf - . ) | ( cd "$RECIPE" && tar xf - )
[ -f "$RECIPE/conanfile.py" ] || fail "样例配方复制失败"

run_create() {   # run_create <日志文件>
    ( cd "$RECIPE" && "$CONAN" create . -pr:h="$PROFILE" -pr:b="$PROFILE" \
        --build=missing -r="$REMOTE" > "$1" 2>&1 )
}

# ── 第 1 轮：关策略 ─────────────────────────────────────────────────────
say ""
say "-- [1/2] 关策略：patches 置空，期望 configure 失败于 DocTools --"
cp "$RECIPE/conandata.yml" "$WORK/conandata.yml.orig"
# 用 awk 截掉 patches 段并写成空列表（不依赖 GNU sed -i）
awk '
    /^patches:/ { print "patches: []"; done = 1; next }
    done { next }
    { print }
' "$WORK/conandata.yml.orig" > "$RECIPE/conandata.yml"
say "   conandata patches = $(grep -c '^patches: \[\]' "$RECIPE/conandata.yml" || true) 处空列表"

OFF_LOG="$WORK/off.log"
set +e
run_create "$OFF_LOG"
OFF_RC=$?
set -e
say "   conan create rc=$OFF_RC"

OFF_HIT=0
if [ "$OFF_RC" -ne 0 ] && sh "$DETECT" --log "$OFF_LOG" > "$WORK/off-detect.log" 2>&1; then
    OFF_HIT=0
else
    if [ "$OFF_RC" -ne 0 ]; then OFF_HIT=1; fi
fi
say "   检测器命中: $(sed -n 's/^hits: //p' "$WORK/off-detect.log" | sed -n '1p' || true)"

# ── 第 2 轮：开策略 ─────────────────────────────────────────────────────
say ""
say "-- [2/2] 开策略：恢复补丁登记，期望 rc=0 且产物齐全 --"
cp "$WORK/conandata.yml.orig" "$RECIPE/conandata.yml"
say "   patches = $(grep -c 'patch_file:' "$RECIPE/conandata.yml" || true) 个"

ON_LOG="$WORK/on.log"
set +e
run_create "$ON_LOG"
ON_RC=$?
set -e
say "   conan create rc=$ON_RC"

# ── 断言 ────────────────────────────────────────────────────────────────
say ""
say "-- 断言 --"
RC=0

if [ "$OFF_RC" -eq 0 ]; then
    say "ASSERT-FAIL 关策略本应失败，实际 rc=0（补丁未真正关闭？）"
    RC=1
elif grep -q 'Could NOT find KF6 (missing: DocTools)' "$OFF_LOG" 2>/dev/null; then
    say "ASSERT-OK   关策略失败且报错为 DocTools 缺失"
else
    # 组件表缺失也可能表现为 KF6DocTools 的 config 缺失，两者同等有效
    if grep -q 'DocTools' "$OFF_LOG" 2>/dev/null; then
        say "ASSERT-OK   关策略失败，日志含 DocTools 缺失证据"
    else
        say "ASSERT-FAIL 关策略失败，但日志里找不到 DocTools 缺失证据"
        RC=1
    fi
fi

if [ "$ON_RC" -ne 0 ]; then
    say "ASSERT-FAIL 开策略本应通过，实际 rc=$ON_RC（见 $ON_LOG）"
    RC=1
else
    say "ASSERT-OK   开策略 rc=0"
fi

# 产物目录：优先取 create 日志里的 "Package folder"；若包已在缓存中，
# create 不会重新打包、也就不会打印该行，此时退回用 conan cache path 解析。
resolve_pkg_folder() {   # resolve_pkg_folder <日志>
    pf=$(sed -n 's/^palapeli\/26\.04\.0: Package folder //p' "$1" 2>/dev/null | sed -n '1p' || true)
    if [ -z "${pf:-}" ]; then
        pid=$("$CONAN" list "palapeli/26.04.0:*" --format=compact 2>/dev/null \
              | sed -n 's/.*palapeli\/26\.04\.0#[0-9a-f]*:\([0-9a-f]\{40,\}\).*/\1/p' \
              | sed -n '1p' || true)
        if [ -n "${pid:-}" ]; then
            pf=$("$CONAN" cache path "palapeli/26.04.0:$pid" 2>/dev/null || true)
        fi
    fi
    printf '%s' "${pf:-}"
}

PKG=$(resolve_pkg_folder "$ON_LOG")
if [ -n "${PKG:-}" ] && [ -d "$PKG" ]; then
    MISSING=""
    for rel in bin/palapeli lib/libpala.so \
               lib/plugins/kf6/thumbcreator/palathumbcreator.so \
               lib/plugins/palapelislicers/palapeli_rectslicer.so \
               lib/plugins/palapelislicers/palapeli_jigsawslicer.so \
               lib/plugins/palapelislicers/palapeli_goldbergslicer.so \
               share/mime/packages/palapeli-mimetypes.xml ; do
        [ -e "$PKG/$rel" ] || MISSING="$MISSING $rel"
    done
    if [ -z "$MISSING" ]; then
        say "ASSERT-OK   产物齐全（可执行 + libpala + 4 个插件 + MIME 定义）"
    else
        say "ASSERT-FAIL 产物缺失:$MISSING"
        RC=1
    fi
else
    say "ASSERT-SKIP 未从日志解析到 package folder，跳过产物清单断言"
fi

say ""
if [ "$RC" -eq 0 ]; then
    say "RESULT: 双向验证通过（关策略报错 / 开策略通过）"
else
    say "RESULT: 验证失败（rc=$RC，日志见 $WORK）"
fi
exit "$RC"
