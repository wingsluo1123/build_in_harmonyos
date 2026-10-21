#!/bin/sh
# detect-kf6-desktop-integration.sh
#   检出「把桌面集成组件当作必需依赖」的 KF6/KDE 工程（DocTools 手册链 / shared-mime-info）
#
# 背景：HarmonyOS PC（OHOS aarch64）上的 KDE 应用普遍在顶层
#   find_package(KF6 ... REQUIRED COMPONENTS ... DocTools ...)
# 里连带要求「文档/手册工具链」，在 mime 子目录里要求 shared-mime-info 的
# update-mime-database。这两者都不是应用的运行期依赖：
#   - DocTools（kdoctools）：制品仓只发布了 6.19.0（其配方拉 karchive/6.19.0、
#     extra-cmake-modules/6.19.0、libxslt、libxml2），与多数应用所在的 6.18/6.26
#     闭包不是同一条版本线；直接引入会撕裂闭包，不引入则 REQUIRED 直接报
#     "Could NOT find KF6 (missing: DocTools)"。
#   - SharedMimeInfo：ECM 的 FindSharedMimeInfo 找的是 update-mime-database 工具，
#     制品仓有 shared-mime-info/2.4、2.5.1 —— 可以用 tool_requires 满足，不必改源码。
#
# 命中语义（与本知识库其它检测脚本一致）：目标平台未声明支持、但源码里当真在用。
#   HARD —— 配置期硬依赖：REQUIRED 组件表里的 DocTools、find_package(KF6DocTools)、
#           kdoctools_install()/kdoctools_create_handbook()/add_subdirectory(doc)、
#           find_package(SharedMimeInfo REQUIRED)、update_xdg_mimetypes()。
#           照原样构建必然在 configure 阶段失败 → 按 strategy.md 处理，脚本 exit 1。
#   LOG  —— 直接喂构建日志（--log）时的报错特征，用于「先复现再处置」的闭环。
#
# 用法:
#   detect-kf6-desktop-integration.sh [--json] [--quiet] <源码目录>
#   detect-kf6-desktop-integration.sh [--json] --log <构建日志>
# 退出码:
#   0 = 未命中（无需处理）
#   1 = 命中 HARD（需按 knowledge/operations/kf6-desktop-integration/strategy.md 处理）
#   2 = 用法错误
#
# 纯 POSIX sh + find/grep/sed，可在 OHOS 自带 busybox 上直接跑；不含任何写死的本地路径。

set -eu

JSON=0
QUIET=0
SRC=""
LOG=""

usage() {
    echo "usage: $0 [--json] [--quiet] <source-dir>" >&2
    echo "       $0 [--json] --log <build-log>" >&2
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --json) JSON=1 ;;
        --quiet) QUIET=1 ;;
        --log)
            shift
            [ $# -gt 0 ] || usage
            LOG="$1"
            ;;
        -h|--help) usage ;;
        *)
            if [ -n "$SRC" ]; then usage; fi
            SRC="$1"
            ;;
    esac
    shift
done

if [ -z "$LOG" ]; then
    if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
        echo "FAIL: source directory not found: '${SRC}'" >&2
        usage
    fi
else
    if [ ! -f "$LOG" ]; then
        echo "FAIL: build log not found: '${LOG}'" >&2
        exit 2
    fi
fi

TMP_BASE="${TMPDIR:-.}"
HITS="$TMP_BASE/.detect-kf6-di-$$.tsv"
trap 'rm -f "$HITS"' EXIT INT TERM
: > "$HITS"

rec() {   # rec <level> <where> <text>
    # 控制字符与制表符归一为空格，保证 TSV/JSON 都合法
    text=$(printf '%s' "$3" | tr -d '\000-\010\013-\037' | tr '\t' ' ')
    printf '%s\t%s\t%s\n' "$1" "$2" "$text" >> "$HITS"
}

# ── 源码侧 ───────────────────────────────────────────────────────────────
# 只看构建描述文件：CMake 的组件必需性只在这一层表达。
scan_source() {
    dir=$1
    FILES="$TMP_BASE/.detect-kf6-di-files-$$.txt"
    find "$dir" -type f \
        \( -name 'CMakeLists.txt' -o -name '*.cmake' -o -name '*.cmake.in' \) \
        -not -path '*/.git/*' -not -path '*/build/*' -not -path '*/.build/*' \
        > "$FILES" 2>/dev/null || true

    # 1) KF6 的 REQUIRED 组件表里出现 DocTools（跨行看：find_package(KF6 ... )
    awk '
        FNR == 1 { inblock = 0 }
        {
            line = $0
            if (!inblock && line ~ /find_package[ \t]*\([ \t]*KF6([ \t]|$)/) { inblock = 1 }
            if (inblock) {
                if (line ~ /(^|[^A-Za-z0-9_])DocTools([^A-Za-z0-9_]|$)/) {
                    printf "%s:%d:%s\n", FILENAME, FNR, line
                }
                if (line ~ /\)/) { inblock = 0 }
            }
        }
    ' $(cat "$FILES") 2>/dev/null | sed 's|^|HARD\tdoc-tools-component\t|' >> "$HITS" || true

    # 2) 直接查 KF6DocTools / 手册生成 / 文档子目录 / MIME 工具
    #    整行注释（`#` 开头）里的示例写法不算命中：注释不参与 configure。
    hit() {   # hit <kind> <ERE>
        grep -Hn -E "$2" $(cat "$FILES") 2>/dev/null \
            | grep -v -E '^[^:]*:[0-9]+:[[:space:]]*#' \
            | sed "s|^|HARD\t$1\t|" >> "$HITS" || true
    }
    hit doc-tools-find-package   'find_package[[:space:]]*\([[:space:]]*KF6DocTools'
    hit doc-tools-install-po     'kdoctools_install[[:space:]]*\('
    hit doc-tools-handbook       'kdoctools_create_handbook[[:space:]]*\('
    hit doc-subdirectory         'add_subdirectory[[:space:]]*\([[:space:]]*doc[[:space:]]*\)'
    hit mime-find-package-required 'find_package[[:space:]]*\([[:space:]]*SharedMimeInfo[[:space:]]+REQUIRED'
    hit mime-update-xdg          'update_xdg_mimetypes[[:space:]]*\('

    rm -f "$FILES"
}

# ── 日志侧 ───────────────────────────────────────────────────────────────
scan_log() {
    f=$1
    # CMake 的 REQUIRED 组件缺失：整段（含 Reason given by package）都收，便于对照
    grep -n -E 'Could NOT find KF6.*missing:.*DocTools|Missing the following required components:.*DocTools' "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-kf6-missing-doctools\t/' >> "$HITS" || true
    grep -n -E 'Could NOT find SharedMimeInfo|Could not find a package configuration file provided by "SharedMimeInfo"' "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-missing-sharedmimeinfo\t/' >> "$HITS" || true
    grep -n -E 'Unknown CMake command "(kdoctools_install|kdoctools_create_handbook)"' "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-unknown-kdoctools-command\t/' >> "$HITS" || true
}

if [ -n "$LOG" ]; then
    scan_log "$LOG"
else
    scan_source "$SRC"
fi

HARD=$(grep -c '^HARD' "$HITS" 2>/dev/null || true)
[ -n "${HARD:-}" ] || HARD=0
TOTAL=$HARD

if [ "$JSON" = "1" ]; then
    printf '{"scanned":"%s","hard_hits":%s,"hits":[' "$(printf '%s' "${LOG:-$SRC}" | sed 's/\\/\\\\/g; s/"/\\"/g')" "$HARD"
    first=1
    while IFS='	' read -r level where text; do
        [ -n "${level:-}" ] || continue
        esc_where=$(printf '%s' "$where" | sed 's/\\/\\\\/g; s/"/\\"/g')
        esc_text=$(printf '%s' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g')
        [ "$first" = "1" ] || printf ','
        first=0
        printf '{"level":"%s","kind":"%s","text":"%s"}' "$level" "$esc_where" "$esc_text"
    done < "$HITS"
    printf ']}\n'
else
    if [ "$QUIET" = "0" ]; then
        while IFS='	' read -r level where text; do
            [ -n "${level:-}" ] || continue
            printf '%s %s: %s\n' "$level" "$where" "$text"
        done < "$HITS"
    fi
    echo "hits: hard=$HARD total=$TOTAL"
fi

if [ "$HARD" -gt 0 ]; then
    exit 1
fi
exit 0
