#!/bin/sh
# detect-gui-toolkit-backend-macro-guard.sh
#   检出「源码级消费者无条件使用 GUI 工具库的后端专属 API，而目标平台的该后端未启用」的工程。
#
# 背景：HarmonyOS PC（OHOS aarch64）上的 gtk/3.24.x 制品是 **broadway-only** 构建
# （gdkconfig.h 里 #undef GDK_WINDOWING_X11 / #define GDK_WINDOWING_BROADWAY），
# X11/Wayland/Win32/Quartz 的专用头（gdk/gdkx.h 等）根本不随包安装。任何源码级消费者
# （C/C++ 应用、语言绑定、插件）只要无条件 include 这类头或调用后端专属符号，编译必失败；
# 而工具包自身（gtk/gtkplug.h:34 `#ifdef GDK_WINDOWING_X11`）的契约是「这些 API 只在
# 对应后端宏下存在」——所以正确修法是用**工具包自己发布的后端宏**做源码守卫，
# 既不是无条件 -D 强开宏，也不是按平台名（__OHOS__）硬编码分支。
#
# 命中语义（与本知识库其它检测脚本一致）：目标平台未启用该后端、但源码里当真在用。
#   HARD —— 无条件 include 后端专用头 / 直接调用后端专属符号，且所在文件没有对应的
#           `#if defined(<BACKEND>_WINDOWING_*)` 守卫；照原样构建必然编译失败
#           → 按 strategy.md 处理，脚本 exit 1。
#   WARN —— 有守卫但只覆盖 include、未覆盖函数体（链接期隐藏爆炸点的常见形态）；
#            或守卫宏不是工具包发布的后端宏（平台名/自定义宏）。
#   LOG  —— 直接喂构建日志（--log）时的报错特征，用于「先复现再处置」的闭环。
#
# 用法:
#   detect-gui-toolkit-backend-macro-guard.sh [--json] [--quiet] <源码目录>
#   detect-gui-toolkit-backend-macro-guard.sh [--json] --log <构建日志>
#
# 退出码:
#   0 = 未命中（无需处理）
#   1 = 命中 HARD（需按 knowledge/operations/gui-toolkit-backend-macro-guard/strategy.md 处理）
#   2 = 用法错误
#
# 纯 POSIX sh + find/grep/sed/awk，可在 OHOS 自带 busybox 上直接跑；
# 不含任何写死的本地路径，不依赖本机 conan 缓存位置。

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
HITS="$TMP_BASE/.detect-gtk-backend-$$.tsv"
FILES="$TMP_BASE/.detect-gtk-backend-files-$$.txt"
trap 'rm -f "$HITS" "$FILES"' EXIT INT TERM
: > "$HITS"

rec() {   # rec <level> <kind> <text>
    text=$(printf '%s' "$3" | tr -d '\000-\010\013-\037' | tr '\t' ' ')
    printf '%s\t%s\t%s\n' "$1" "$2" "$text" >> "$HITS"
}

# 后端专属头 → 守卫宏。键是头文件名的一部分，值是工具包发布的后端宏。
# gtk3/gdk 系：后端宏集合由 gdkconfig.h 发布（GDK_WINDOWING_*）。
BACKEND_HEADERS='gdkx\.h:GDK_WINDOWING_X11
gdkwayland\.h:GDK_WINDOWING_WAYLAND
gdkwin32\.h:GDK_WINDOWING_WIN32
gdkquartz\.h:GDK_WINDOWING_QUARTZ
gdkbroadway\.h:GDK_WINDOWING_BROADWAY'

# 后端专属符号（无头文件也可能直接调用）→ 守卫宏
BACKEND_SYMBOLS='GDK_DISPLAY_XDISPLAY:GDK_WINDOWING_X11
GDK_WINDOW_XID:GDK_WINDOWING_X11
GDK_SCREEN_XDISPLAY:GDK_WINDOWING_X11
GDK_WINDOW_XWINDOW:GDK_WINDOWING_X11
gdk_x11_[A-Za-z_]+:GDK_WINDOWING_X11
XGrabKey:GDK_WINDOWING_X11
XStringToKeysym:GDK_WINDOWING_X11
XKeysymToKeycode:GDK_WINDOWING_X11
gdk_wayland_[A-Za-z_]+:GDK_WINDOWING_WAYLAND
gdk_win32_[A-Za-z_]+:GDK_WINDOWING_WIN32
gdk_quartz_[A-Za-z_]+:GDK_WINDOWING_QUARTZ'

# ── 源码侧 ───────────────────────────────────────────────────────────────
scan_source() {
    dir=$1
    find "$dir" -type f \
        \( -name '*.c' -o -name '*.h' -o -name '*.cc' -o -name '*.cpp' \
           -o -name '*.cxx' -o -name '*.hpp' -o -name '*.hh' -o -name '*.m' -o -name '*.mm' \) \
        -not -path '*/.git/*' -not -path '*/build/*' -not -path '*/.build/*' \
        -not -path '*/vendor/*' -not -path '*/third_party/*' \
        > "$FILES" 2>/dev/null || true
    [ -s "$FILES" ] || return 0

    # 判一个文件是否在某个后端宏的守卫之下。算守卫的形态（与工具包自身写法一致）：
    #   #if defined(<MACRO>) / #if defined <MACRO> / #elif 同上（含 && 组合）
    #   #ifdef <MACRO> / #elifdef <MACRO>
    # 不算守卫（语义相反：代码在宏「未定义」时才编译，正是后端缺失时必炸的写法）：
    #   #ifndef <MACRO> / #if !defined(<MACRO>)
    # 行内 /* */ 与 // 注释先剥掉，避免注释里出现的 defined(<MACRO>) 被误当守卫。
    guarded_by() {   # guarded_by <file> <macro>
        awk -v m="$2" '
            {   line = $0
                sub(/\/\*.*\*\//, " ", line)
                sub(/\/\/.*$/, "", line)
                sub(/^[[:space:]]*#[[:space:]]*/, "#", line)
                if (line ~ /^#(if|elif)def[[:space:]]+/) {
                    s = line
                    sub(/^#(if|elif)def[[:space:]]+/, "", s)
                    sub(/[^A-Za-z0-9_].*$/, "", s)
                    if (s == m) { found = 1; exit } else { next }
                }
                if (line ~ /^#(if|elif)[[:space:]]/) {
                    if (line ~ ("(^|[^A-Za-z0-9_])![[:space:]]*defined[[:space:]]*[(]?[[:space:]]*" m "([^A-Za-z0-9_]|$)")) next
                    if (line ~ ("(^|[^A-Za-z0-9_])defined[[:space:]]*[(]?[[:space:]]*" m "([^A-Za-z0-9_]|$)")) { found = 1; exit }
                }
            }
            END { exit(found ? 0 : 1) }' "$1" 2>/dev/null
    }

    # 逐文件 grep —— 不用 $(cat "$FILES")：路径含空格/通配符会被 shell 分词而漏扫
    grep_files() {   # grep_files <grep 选项...>，文件列表取自 "$FILES"
        while IFS= read -r f; do
            [ -n "$f" ] || continue
            grep "$@" -- "$f" 2>/dev/null || true
        done < "$FILES"
    }

    check_hits() {   # check_hits <regex> <macro> <kind-prefix>
        grep_files -Hn -E "$1" \
            | grep -v -E '^[^:]*:[0-9]+:[[:space:]]*(//|\*|/\*)' \
            | while IFS= read -r line; do
                  f=${line%%:*}
                  if guarded_by "$f" "$2"; then
                      rec WARN "${3}-guarded" "$line"
                  else
                      rec HARD "${3}-unguarded" "$line"
                  fi
              done
    }

    printf '%s\n' "$BACKEND_HEADERS" | while IFS=: read -r hdr macro; do
        [ -n "${hdr:-}" ] || continue
        # 头文件可能带 gdk/ 前缀、也可能写成 <gdkx.h> / "gdk/gdkx.h"，三种都要命中
        check_hits "#[[:space:]]*include[[:space:]]*[<\"]([^>\"]*/)?${hdr}[>\"]" "$macro" "backend-header"
    done

    printf '%s\n' "$BACKEND_SYMBOLS" | while IFS=: read -r sym macro; do
        [ -n "${sym:-}" ] || continue
        check_hits "(^|[^A-Za-z0-9_])${sym}([^A-Za-z0-9_]|$)" "$macro" "backend-symbol"
    done

    # 平台名硬编码守卫：命中即 WARN（能力探测优于平台名）。defined(X) 与 #ifdef X 两种写法都算
    grep_files -Hn -E '(defined[[:space:]]*\([[:space:]]*|ifdef[[:space:]]+)(__OHOS__|OHOS|__HARMONYOS__)([^A-Za-z0-9_]|$)' \
        | sed 's|^|WARN\tplatform-macro-guard\t|' >> "$HITS" || true

    rm -f "$FILES"
}

# ── 日志侧 ───────────────────────────────────────────────────────────────
scan_log() {
    f=$1
    # 后端专用头缺失（clang/gcc 两种措辞）
    grep -n -E "fatal error: '(gdk/gdkx|gdk/gdkwayland|gdk/gdkwin32|gdk/gdkquartz)\.h' file not found" "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-backend-header-missing\t/' >> "$HITS" || true
    # 后端专属宏未声明（头被包含但宏不存在，或宏本身来自该后端）
    grep -n -E "use of undeclared identifier '(AnyPropertyType|None|GDK_DISPLAY_XDISPLAY|GDK_WINDOW_XID|gdk_x11_[A-Za-z_]+)'" "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-backend-symbol-undeclared\t/' >> "$HITS" || true
    # 后端专属函数隐式声明 → 类型不兼容（未声明函数族）
    grep -n -E "implicit declaration of function '[A-Za-z_0-9]*(XGrabKey|XKeysymToKeycode|gdk_x11_[A-Za-z_0-9]*|gtk_plug_new)'" "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-backend-symbol-implicit\t/' >> "$HITS" || true
    grep -n -E "incompatible integer to pointer conversion passing 'int' to parameter of type .*GtkWidget \*" "$f" 2>/dev/null \
        | sed 's/^/HARD\tlog-implicit-decl-fallout\t/' >> "$HITS" || true
    # 链接期隐藏爆炸点：守卫只盖了 include，函数体仍引用后端 get_type
    grep -n -E "undefined reference to .(gdk_x11_[A-Za-z_0-9]*|gtk_plug_get_type|gtk_socket_get_type)" "$f" 2>/dev/null \
        | sed 's/^/WARN\tlog-link-backend-symbol\t/' >> "$HITS" || true
}

if [ -n "$LOG" ]; then
    scan_log "$LOG"
else
    scan_source "$SRC"
fi

HARD=$(grep -c '^HARD' "$HITS" 2>/dev/null || true)
[ -n "${HARD:-}" ] || HARD=0
WARN=$(grep -c '^WARN' "$HITS" 2>/dev/null || true)
[ -n "${WARN:-}" ] || WARN=0
TOTAL=$((HARD + WARN))

if [ "$JSON" = "1" ]; then
    printf '{"scanned":"%s","hard_hits":%s,"warn_hits":%s,"hits":[' \
        "$(printf '%s' "${LOG:-$SRC}" | sed 's/\\/\\\\/g; s/"/\\"/g')" "$HARD" "$WARN"
    first=1
    while IFS='	' read -r level kind text; do
        [ -n "${level:-}" ] || continue
        esc_kind=$(printf '%s' "$kind" | sed 's/\\/\\\\/g; s/"/\\"/g')
        esc_text=$(printf '%s' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g')
        [ "$first" = "1" ] || printf ','
        first=0
        printf '{"level":"%s","kind":"%s","text":"%s"}' "$level" "$esc_kind" "$esc_text"
    done < "$HITS"
    printf ']}\n'
else
    if [ "$QUIET" = "0" ]; then
        while IFS='	' read -r level kind text; do
            [ -n "${level:-}" ] || continue
            printf '%s %s: %s\n' "$level" "$kind" "$text"
        done < "$HITS"
    fi
    echo "hits: hard=$HARD warn=$WARN total=$TOTAL"
fi

if [ "$HARD" -gt 0 ]; then
    exit 1
fi
exit 0
