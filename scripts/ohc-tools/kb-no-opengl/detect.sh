#!/bin/sh
# detect.sh — Qt6 下游代码在「无 OpenGL」的 OHOS Qt 构建下编译失败：检测（只读）
#
# 共性问题（KB-NO-OPENGL）：
#   OHOS 版 qtbase/6.11.x 未构建 OpenGL 模块——qtgui-config.h 里
#   `#define QT_FEATURE_opengl -1` 且 `#define QT_NO_OPENGL 1`，
#   QtOpenGL / QtOpenGLWidgets 头目录与 Qt6OpenGL cmake 包整体缺失。
#   下游 Qt6 代码一旦直接使用 QOpenGLContext / QOpenGLFunctions / glXxx，
#   失败形态极具误导性：
#     - `#include <QOpenGLContext>` **能成功**（头文件在，整个内容被
#       #ifndef QT_NO_OPENGL 包空），报错是
#       `error: use of undeclared identifier 'QOpenGLContext'`；
#     - `#include <QOpenGLWidget>` 才是 `file not found`（QtOpenGLWidgets 缺失）。
#   于是极易被误判成「头文件路径 / 包含顺序 / 编译参数」问题，白白排查。
#
# 用法：
#   detect.sh --src <源码目录> [--qt-prefix <Qt前缀>] [--build-dir <CMake构建目录>]
#             [--log <构建日志>] [--json]
#
#   退出码（位或）：0=未命中  1=源码使用 GL API  2=目标 Qt 无 OpenGL  4=日志命中特征错误
#   --json 时 JSON 摘要输出到 stdout，诊断文本走 stderr。
#
# 本脚本只读，不修改任何文件；POSIX sh，可在 OHOS aarch64 与普通 Linux 上运行。

set -u

SRC=""
QT_PREFIX=""
BUILD_DIR=""
LOG=""
JSON=0

while [ $# -gt 0 ]; do
    case "$1" in
        --src)        SRC="$2"; shift 2 ;;
        --qt-prefix)  QT_PREFIX="$2"; shift 2 ;;
        --build-dir)  BUILD_DIR="$2"; shift 2 ;;
        --log)        LOG="$2"; shift 2 ;;
        --json)       JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

[ -z "$SRC" ] && { echo "ERROR: --src required" >&2; exit 64; }
[ -d "$SRC" ] || { echo "ERROR: not a directory: $SRC" >&2; exit 64; }

HIT_A=0   # 源码使用 GL API
HIT_B=0   # 目标 Qt 无 OpenGL
HIT_C=0   # 日志特征
DETAIL_A=""
DETAIL_B=""
DETAIL_C=""
A_HITS=""

# GL API 词表：Qt 封装类 + 原始 GL 调用（限定调用形态，避免把 glContext 之类变量名当调用）
GL_QT_RE='QOpenGL[A-Za-z]+'
GL_CALL_RE='(^|[^A-Za-z0-9_])gl[A-Z][A-Za-z0-9_]*[[:space:]]*\('
GL_INC_RE='#include[[:space:]]*[<"](QOpenGL|QtOpenGL|QtGui/qopengl)'
CMAKE_GL_RE='Qt6::OpenGL|Qt::OpenGL|OpenGLWidgets|QT_OPENGL|find_package\(Qt6[^)]*[[:space:]]OpenGL'

# ---------- 通道 A：源码特征 ----------
scan_src() {
    # $1 = 目录；$2 = 描述标签
    _dir="$1"
    _tag="$2"
    [ -d "$_dir" ] || return 0
    _n="$({ grep -REl "$GL_QT_RE" "$_dir" \
              --include='*.cpp' --include='*.cc' --include='*.cxx' \
              --include='*.h' --include='*.hpp' --include='*.hh' 2>/dev/null
            grep -REl "$GL_QT_RE" "$_dir" --include='CMakeLists.txt' --include='*.cmake' 2>/dev/null; } \
          | grep -Ev '/(3rdparty|third_party|vendor|\.git)/' | sort -u | wc -l | tr -d ' ')"
    if [ "$_n" -gt 0 ]; then
        HIT_A=1
        _list="$({ grep -REl "$GL_QT_RE" "$_dir" \
                     --include='*.cpp' --include='*.cc' --include='*.cxx' \
                     --include='*.h' --include='*.hpp' --include='*.hh' 2>/dev/null
                   grep -REl "$GL_QT_RE" "$_dir" --include='CMakeLists.txt' --include='*.cmake' 2>/dev/null; } \
                 | grep -Ev '/(3rdparty|third_party|vendor|\.git)/' | sort -u | head -10)"
        A_HITS="$_list"
        DETAIL_A="$_tag: $_n source file(s) reference QOpenGL* API"
    fi
}

scan_src "$SRC" "src"

# 源码子通道：包含形态与 CMake 形态（用于区分「头缺失」还是「符号缺失」）
INC_HITS="$({ grep -REl "$GL_INC_RE" "$SRC" \
              --include='*.cpp' --include='*.cc' --include='*.cxx' \
              --include='*.h' --include='*.hpp' 2>/dev/null | head -5; })"
CMAKE_HITS="$({ grep -REl "$CMAKE_GL_RE" "$SRC" \
                --include='CMakeLists.txt' --include='*.cmake' 2>/dev/null | head -5; })"

# ---------- 通道 B：目标 Qt 是否带 OpenGL ----------
resolve_qt_prefix() {
    if [ -n "$QT_PREFIX" ] && [ -d "$QT_PREFIX" ]; then
        echo "$QT_PREFIX"; return 0
    fi
    if [ -n "$BUILD_DIR" ] && [ -f "$BUILD_DIR/CMakeCache.txt" ]; then
        _d="$(grep -m1 -oE 'Qt6Gui_DIR:[A-Z]+=[^ ]+' "$BUILD_DIR/CMakeCache.txt" 2>/dev/null | cut -d= -f2)"
        if [ -n "$_d" ]; then
            # <prefix>/lib/cmake/Qt6Gui → <prefix>
            echo "$_d" | sed 's#/lib/cmake/Qt6Gui$##'
            return 0
        fi
    fi
    if [ -n "${QTDIR:-}" ] && [ -f "$QTDIR/include/QtGui/qtgui-config.h" ]; then
        echo "$QTDIR"; return 0
    fi
    if [ -n "${Qt6Gui_DIR:-}" ]; then
        echo "$Qt6Gui_DIR" | sed 's#/lib/cmake/Qt6Gui$##'
        return 0
    fi
    echo ""
}

QP="$(resolve_qt_prefix)"
CFG="$QP/include/QtGui/qtgui-config.h"
if [ -z "$QP" ]; then
    DETAIL_B="qt prefix unresolved (pass --qt-prefix or --build-dir); OpenGL availability unchecked"
elif [ ! -f "$CFG" ]; then
    DETAIL_B="qtgui-config.h not found under $QP (not a Qt6 Gui prefix?); unchecked"
else
    FEATURE="$(grep -m1 -oE '^#define QT_FEATURE_opengl .*' "$CFG" 2>/dev/null | awk '{print $3}')"
    NOGL="$(grep -c '^#define QT_NO_OPENGL' "$CFG" 2>/dev/null | tr -d ' ')"
    MOD_CMAKE="yes"; [ -d "$QP/lib/cmake/Qt6OpenGL" ] || MOD_CMAKE="no"
    MOD_INC="yes";   [ -d "$QP/include/QtOpenGL" ]  || MOD_INC="no"
    if [ "${FEATURE:-}" = "-1" ] || [ "${NOGL:-0}" != "0" ] || [ "$MOD_CMAKE" = "no" ] || [ "$MOD_INC" = "no" ]; then
        HIT_B=1
        DETAIL_B="target Qt has NO OpenGL: QT_FEATURE_opengl=${FEATURE:-?} QT_NO_OPENGL=$([ "${NOGL:-0}" != "0" ] && echo yes || echo no) Qt6OpenGL_cmake=$MOD_CMAKE QtOpenGL_include=$MOD_INC (prefix=$QP)"
    else
        DETAIL_B="target Qt provides OpenGL (prefix=$QP)"
    fi
fi

# ---------- 通道 C：构建日志特征 ----------
# 关键：OHOS 下的首要特征是 "use of undeclared identifier 'QOpenGL...'"（含头成功、
# 符号未声明），而不是 file not found——后者只在 QtOpenGLWidgets 头（QOpenGLWidget）出现。
if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    C1="$(grep -cE "use of undeclared identifier '(QOpenGL|glContext|gl[A-Z])" "$LOG" 2>/dev/null | tr -d ' ')"
    C2="$(grep -cE "unknown type name 'QOpenGL|no member named '.*' in namespace 'QOpenGL" "$LOG" 2>/dev/null | tr -d ' ')"
    C3="$(grep -cE "'QOpenGLWidget' file not found|QOpenGLWidget: No such file" "$LOG" 2>/dev/null | tr -d ' ')"
    C4="$(grep -cE "Qt6OpenGLConfig\.cmake|Qt6::OpenGL.*not found|Could NOT find Qt6OpenGL|provided.*FindQt6OpenGL\.cmake" "$LOG" 2>/dev/null | tr -d ' ')"
    C5="$(grep -cE "error: use of undeclared identifier 'QOpenGLFunctions'|cannot initialize a variable of type 'QOpenGLFunctions" "$LOG" 2>/dev/null | tr -d ' ')"
    C_SUM=$(( C1 + C2 + C3 + C4 + C5 ))
    if [ "$C_SUM" -gt 0 ]; then
        HIT_C=1
        DETAIL_C="log hits: undeclared-symbol=$((C1 + C2 + C5)) missing-widget-header=$C3 missing-cmake-package=$C4"
    fi
fi

RC=$(( HIT_A + HIT_B * 2 + HIT_C * 4 ))

if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-NO-OPENGL","hit_a":%d,"hit_b":%d,"hit_c":%d,"rc":%d,' \
        "$HIT_A" "$HIT_B" "$HIT_C" "$RC"
    printf '"detail_a":"%s","detail_b":"%s","detail_c":"%s",' "$DETAIL_A" "$DETAIL_B" "$DETAIL_C"
    printf '"source_files":"%s","cmake_files":"%s"}\n' \
        "$(echo "$A_HITS" | tr '\n' ',')" "$(echo "$CMAKE_HITS" | tr '\n' ',')"
else
    if [ "$RC" -eq 0 ]; then
        echo "KB-NO-OPENGL: no hit (no GL API in sources, target Qt state unknown/ok)"
    else
        [ "$HIT_A" -eq 1 ] && echo "KB-NO-OPENGL HIT-A: $DETAIL_A"
        [ "$HIT_B" -eq 1 ] && echo "KB-NO-OPENGL HIT-B: $DETAIL_B"
        [ "$HIT_C" -eq 1 ] && echo "KB-NO-OPENGL HIT-C: $DETAIL_C"
        [ -n "$INC_HITS" ]   && echo "  GL includes:"   && echo "$INC_HITS"   | sed 's/^/    /'
        [ -n "$CMAKE_HITS" ] && echo "  CMake OpenGL references:" && echo "$CMAKE_HITS" | sed 's/^/    /'
        [ -n "$A_HITS" ]     && echo "  GL API sources (top 10):" && echo "$A_HITS" | sed 's/^/    /'
    fi
    [ "$HIT_B" -eq 1 ] && [ -n "$QP" ] && echo "  probe: $CFG"
fi
exit "$RC"
