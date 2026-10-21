#!/bin/sh
# reproduce.sh — 「GUI 工具库后端专属 API」问题的双向复现脚本
#
#   关守卫（原始源码） → 检测器命中 HARD 且编译报 'gdk/gdkx.h' file not found
#   开守卫（打补丁后） → 检测器 HARD=0 且 key_grabber.c 编译通过
#
# 依赖：项目内 clang（或 $CC）、gtk/3.24.x 的制品前缀（broadway-only 构建）。
# 不含任何写死的本地路径：GTK 前缀优先取 --gtk-prefix，其次从 $CONAN_HOME 缓存
# 里探测（存在多个时取兼容 broadway-only 的那个），最后回落到 pkg-config。
#
# 用法:
#   ./reproduce.sh
#   ./reproduce.sh --tarball /path/to/pa-applet-g20181009.tar.gz
#   ./reproduce.sh --gtk-prefix /path/to/gtk-package-prefix
#
# 退出码: 0 = 双向验证通过；1 = 不符合预期；2 = 用法/环境错误

set -eu

URL="https://codeload.github.com/fernandotcl/pa-applet/tar.gz/3b4f8b3"
SHA256="32dcd0663cca120cf60d1046443884f854448e7bb71226a416915ae9beb33e11"
TARBALL=""
GTK_PREFIX=""
KEEP=0

usage() {
    echo "usage: $0 [--tarball <file>] [--gtk-prefix <dir>] [--keep]" >&2
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --tarball) shift; [ $# -gt 0 ] || usage; TARBALL="$1" ;;
        --gtk-prefix) shift; [ $# -gt 0 ] || usage; GTK_PREFIX="$1" ;;
        --keep) KEEP=1 ;;
        -h|--help) usage ;;
        *) usage ;;
    esac
    shift
done

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DETECT="$HERE/detect-gui-toolkit-backend-macro-guard.sh"
PATCH="$HERE/sample/pa-applet/patches/0001-guard-x11-key-grabber.patch"
[ -f "$DETECT" ] || { echo "FAIL: detector not found: $DETECT" >&2; exit 2; }
[ -f "$PATCH" ] || { echo "FAIL: sample patch not found: $PATCH" >&2; exit 2; }

# ── 0. 守卫形态矩阵（离线，不需要 GTK/conan/网络，先跑） ────────────────
# 覆盖 #if defined / #ifdef / #elif defined 与 #ifndef / !defined / 平台名宏等写法，
# 防止「守卫识别」本身退化（例如只认 #if defined 而把 #ifdef 误判成未守卫）。
GUARD_CHECK="$HERE/sample/guard-forms/check.sh"
if [ -f "$GUARD_CHECK" ]; then
    echo "== 守卫形态矩阵（离线） =="
    sh "$GUARD_CHECK" || { echo "FAIL: 守卫形态矩阵不符合预期" >&2; exit 1; }
    echo ""
fi

CC_BIN="${CC:-clang}"
command -v "$CC_BIN" >/dev/null 2>&1 || { echo "FAIL: compiler not found: $CC_BIN" >&2; exit 2; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/repro-gtk-backend.XXXXXX")
trap '[ "$KEEP" = "1" ] || rm -rf "$WORK"' EXIT INT TERM
echo "workdir: $WORK"

# ── 1. 取源码包 ─────────────────────────────────────────────────────────
if [ -z "$TARBALL" ]; then
    TARBALL="$WORK/pa-applet-g20181009.tar.gz"
    echo "== 下载源码包 =="
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --max-time 300 -o "$TARBALL" "$URL" || { echo "FAIL: download failed; use --tarball" >&2; exit 2; }
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$TARBALL" "$URL" || { echo "FAIL: download failed; use --tarball" >&2; exit 2; }
    else
        echo "FAIL: neither curl nor wget available; use --tarball" >&2
        exit 2
    fi
fi
[ -f "$TARBALL" ] || { echo "FAIL: tarball not found: $TARBALL" >&2; exit 2; }

GOT=$(sha256sum "$TARBALL" 2>/dev/null | cut -d' ' -f1)
[ "$GOT" = "$SHA256" ] || { echo "FAIL: sha256 mismatch (got $GOT)" >&2; exit 2; }
echo "OK: sha256 校验通过"

# ── 2. 定位 GTK 前缀（broadway-only 构建才有意义） ──────────────────────
find_gtk_prefix() {
    [ -n "$GTK_PREFIX" ] && { printf '%s\n' "$GTK_PREFIX"; return 0; }
    CH="${CONAN_HOME:-$HOME/.conan2}"
    for d in "$CH"/p/*/p; do
        if [ -f "$d/include/gtk-3.0/gdk/gdkconfig.h" ]; then
            printf '%s\n' "$d"
            return 0
        fi
    done
    return 1
}

GTK=$(find_gtk_prefix || true)
if [ -z "${GTK:-}" ]; then
    echo "FAIL: 找不到 gtk/3.24.x 制品前缀；请用 --gtk-prefix 指定（或先 conan install gtk/3.24.43）" >&2
    exit 2
fi
echo "GTK prefix: $GTK"

# 后端事实：必须确认 X11 后端未启用，否则本复现没有意义
grep -q 'GDK_WINDOWING_X11' "$GTK/include/gtk-3.0/gdk/gdkconfig.h" || {
    echo "FAIL: $GTK 的 gdkconfig.h 未声明 GDK_WINDOWING_*（不是 GTK3 前缀？）" >&2; exit 2; }
if grep -qE '^[[:space:]]*#define[[:space:]]+GDK_WINDOWING_X11' "$GTK/include/gtk-3.0/gdk/gdkconfig.h"; then
    echo "WARN: 该 GTK 构建启用了 X11 后端，本复现的「后端缺失」前提不成立" >&2
fi
if [ -f "$GTK/include/gtk-3.0/gdk/gdkx.h" ]; then
    echo "WARN: gdk/gdkx.h 存在，说明该构建带 X11 后端" >&2
else
    echo "OK: gdk/gdkx.h 不随包安装（broadway-only 契约成立）"
fi

# 组装 include 路径。GTK 的头会连带引入 glib/pango/cairo/gdk-pixbuf/harfbuzz，
# 所以路径必须凑齐：优先用 pkg-config（把同一缓存内所有 pkgconfig 目录都塞进
# PKG_CONFIG_PATH，否则 gtk+-3.0.pc 的 Requires 解不出来），再回落到显式探测。
CH="${CONAN_HOME:-$HOME/.conan2}"
PC_PATH=""
for d in "$CH"/p/*/p/lib/pkgconfig "$GTK/lib/pkgconfig"; do
    [ -d "$d" ] && PC_PATH="${PC_PATH:+$PC_PATH:}$d"
done

INCS="-I$GTK/include/gtk-3.0"
if command -v pkg-config >/dev/null 2>&1 && [ -n "$PC_PATH" ]; then
    PC=$(PKG_CONFIG_PATH="$PC_PATH" pkg-config --cflags gtk+-3.0 2>/dev/null || true)
    [ -n "$PC" ] && INCS="$PC"
fi

# 回落/补齐：按头文件特征在缓存里找同名依赖前缀
for spec in \
    "include/glib-2.0/glib.h:include/glib-2.0" \
    "lib/glib-2.0/include/glibconfig.h:lib/glib-2.0/include" \
    "include/pango-1.0/pango/pango.h:include/pango-1.0" \
    "include/cairo/cairo.h:include/cairo" \
    "include/harfbuzz/hb.h:include/harfbuzz" \
    "include/atk-1.0/atk/atk.h:include/atk-1.0" \
    "include/gdk-pixbuf-2.0/gdk-pixbuf/gdk-pixbuf.h:include/gdk-pixbuf-2.0"; do
    marker=${spec%%:*}
    incdir=${spec##*:}
    for d in "$CH"/p/*/p; do
        if [ -f "$d/$marker" ]; then
            case " $INCS " in
                *" -I$d/$incdir "*) ;;
                *) INCS="$INCS -I$d/$incdir" ;;
            esac
            break
        fi
    done
done

# ── 3. 关侧：原始源码 ───────────────────────────────────────────────────
OFF="$WORK/off"; mkdir -p "$OFF"
tar -xzf "$TARBALL" -C "$OFF" --strip-components=1

echo ""
echo "== 关侧：原始源码 =="
set +e
sh "$DETECT" --quiet "$OFF" > "$WORK/detect-off.log" 2>&1
OFF_DETECT=$?
# shellcheck disable=SC2086
( cd "$OFF" && $CC_BIN -fsyntax-only -std=c99 -D_GNU_SOURCE $INCS -I src src/key_grabber.c ) \
    > "$WORK/compile-off.log" 2>&1
OFF_COMPILE=$?
set -e
tail -n 3 "$WORK/detect-off.log"
echo "detect rc=$OFF_DETECT  compile rc=$OFF_COMPILE"
grep -m1 "gdk/gdkx.h" "$WORK/compile-off.log" >/dev/null 2>&1 || {
    echo "FAIL: 关侧未出现预期的 'gdk/gdkx.h' 报错（见 $WORK/compile-off.log）" >&2; KEEP=1; exit 1; }
sed -n '1,3p' "$WORK/compile-off.log"

# ── 4. 开侧：打补丁 ─────────────────────────────────────────────────────
ON="$WORK/on"; mkdir -p "$ON"
tar -xzf "$TARBALL" -C "$ON" --strip-components=1
( cd "$ON" && git apply -p1 "$PATCH" 2>/dev/null || patch -p1 < "$PATCH" >/dev/null 2>&1 ) || {
    echo "FAIL: 补丁应用失败（检查 patch/git 是否可用，以及补丁 hunk 计数）" >&2; KEEP=1; exit 1; }
grep -q 'GDK_WINDOWING_X11' "$ON/src/key_grabber.c" || {
    echo "FAIL: 补丁未在源码中留下 GDK_WINDOWING_X11 守卫" >&2; KEEP=1; exit 1; }

echo ""
echo "== 开侧：已加后端宏守卫 =="
set +e
sh "$DETECT" --quiet "$ON" > "$WORK/detect-on.log" 2>&1
ON_DETECT=$?
# shellcheck disable=SC2086
( cd "$ON" && $CC_BIN -fsyntax-only -std=c99 -D_GNU_SOURCE $INCS -I src src/key_grabber.c ) \
    > "$WORK/compile-on.log" 2>&1
ON_COMPILE=$?
set -e
tail -n 3 "$WORK/detect-on.log"
echo "detect rc=$ON_DETECT  compile rc=$ON_COMPILE"

# ── 5. 判定 ─────────────────────────────────────────────────────────────
FAIL=0
[ "$OFF_DETECT" -eq 1 ] || { echo "FAIL: 关侧检测器应 exit 1，实得 $OFF_DETECT" >&2; FAIL=1; }
[ "$OFF_COMPILE" -ne 0 ] || { echo "FAIL: 关侧编译应失败，实得 0" >&2; FAIL=1; }
[ "$ON_DETECT" -eq 0 ] || { echo "FAIL: 开侧检测器应 exit 0，实得 $ON_DETECT" >&2; FAIL=1; }
[ "$ON_COMPILE" -eq 0 ] || { echo "FAIL: 开侧编译应成功，实得 $ON_COMPILE（见 $WORK/compile-on.log）" >&2; FAIL=1; }

if [ "$FAIL" -eq 0 ]; then
    echo ""
    echo "RESULT: 双向验证通过（关→报错，开→通过）"
    exit 0
fi
KEEP=1
echo ""
echo "RESULT: 双向验证未通过（workdir 保留：$WORK）"
exit 1
