#!/bin/sh
# fix.sh — KB-NO-OPENGL 修复：给「无 OpenGL 的 Qt6 构建」下的下游代码加 QT_NO_OPENGL 门控
#
# 背景：OHOS 版 qtbase/6.11.x 未构建 OpenGL 模块，qtgui-config.h 里
#       `#define QT_FEATURE_opengl -1` 且 `#define QT_NO_OPENGL 1`。
#       QtGui 下的 qopenglcontext.h / qopenglfunctions.h 全文被
#       `#ifndef QT_NO_OPENGL` 包裹（转发头 <QOpenGLContext> 仍在，
#      所以 #include 能成功、符号却不声明）。
#
# 动作（幂等，可反复执行）：
#   FIX-A include 门控：把成组的 GL include 行包进 #ifndef QT_NO_OPENGL ... #endif
#   FIX-B 语句门控：括号/花括号配对，把以 QOpenGL* 为条件的 if 探测块整块门控
#   FIX-C 单行门控：其他以 GL 调用为主体的独立语句（以 ; 结尾）单独门控
#
# 用法：
#   fix.sh --src <源码目录> [--emit-patch <out.patch>] [--dry-run] [--json]
#
#     --src         源码根（递归处理 .cpp/.cc/.cxx/.h/.hpp/.hh）
#     --emit-patch  把改动导出为 git 风格补丁（可直接放 conan patches/）
#     --dry-run     只报告不落盘
#     --json        机器可读摘要走 stdout（人读信息走 stderr）
#
# 退出码：0=已修复/无需修复  1=参数或 IO 错误  3=存在无法机械判定的区域（需人工补丁）
#
# 只依赖 POSIX sh + awk/grep/diff（OHOS aarch64 与普通 Linux 均可用）；
# 不写死任何本地路径，不读取本地缓存。

set -u

SRC=""
PATCH_OUT=""
DRY=0
JSON=0

while [ $# -gt 0 ]; do
    case "$1" in
        --src)        SRC="$2"; shift 2 ;;
        --emit-patch) PATCH_OUT="$2"; shift 2 ;;
        --dry-run)    DRY=1; shift ;;
        --json)       JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

[ -n "$SRC" ] && [ -d "$SRC" ] || { echo "ERROR: --src <existing dir> required" >&2; exit 64; }

WORK="${TMPDIR:-$PWD}/kb-noopengl.$$"
mkdir -p "$WORK/orig" "$WORK/new" || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

CHANGED_FILES=""
MANUAL_FILES=""
FIXED_A=0
FIXED_B=0
FIXED_C=0

# ---------- 候选文件（跳过第三方/子模块/vendor 树） ----------
CAND="$(grep -REl 'QOpenGL|QtOpenGL|qopengl' "$SRC" \
            --include='*.cpp' --include='*.cc' --include='*.cxx' \
            --include='*.h' --include='*.hpp' --include='*.hh' 2>/dev/null \
        | grep -Ev '/(3rdparty|third_party|vendor|extern|\.git)/' | sort -u)"

[ -z "$CAND" ] && {
    if [ "$JSON" -eq 1 ]; then
        printf '{"kb":"KB-NO-OPENGL","files":0,"fixed_a":0,"fixed_b":0,"fixed_c":0,"manual":0,"rc":0}\n'
    else
        echo "KB-NO-OPENGL fix: nothing to do (no QOpenGL usage found under $SRC)"
    fi
    exit 0
}

# ---------- FIX-A：include 组门控 ----------
AWK_INC='
function isgl(l) {
    return l ~ /^[ \t]*#[ \t]*include[ \t]*[<"](QOpenGL|QtOpenGL|QtGui\/qopengl|QtOpenGLWidgets)/
}
{
    lines[NR] = $0
}
END {
    i = 1
    while (i <= NR) {
        if (isgl(lines[i])) {
            s = i
            while (i <= NR && isgl(lines[i])) i++
            e = i - 1
            if (s > 1 && lines[s-1] ~ /QT_NO_OPENGL/) {
                for (k = s; k <= e; k++) print lines[k]        # 已门控
            } else {
                ind = ""
                if (match(lines[s], /^[ \t]*/)) ind = substr(lines[s], 1, RLENGTH)
                print ind "#ifndef QT_NO_OPENGL"
                for (k = s; k <= e; k++) print lines[k]
                print ind "#endif"
                changed = 1
            }
        } else {
            print lines[i]
            i++
        }
    }
    exit (changed ? 0 : 1)
}
'

# ---------- FIX-B/FIX-C：语句区门控 ----------
# 括号/花括号配对（忽略字符串、字符字面量与注释）；preprocessor 嵌套用 pp_depth 跟踪，
# 已经处在 QT_NO_OPENGL 门控区内的行一律原样透传。
AWK_STMT='
BEGIN { sq = sprintf("%c", 39) }        # 单引号字符（避免非 POSIX 的 \x 转义）
function strip(l,   i, n, c, out, esc) {
    n = length(l); out = ""; i = 1; esc = 0
    while (i <= n) {
        c = substr(l, i, 1)
        if (inblk) {
            if (c == "*" && substr(l, i+1, 1) == "/") { inblk = 0; i += 2; continue }
            i++; continue
        }
        if (instr) {
            if (esc) esc = 0
            else if (c == "\\") esc = 1
            else if (c == "\"") instr = 0
            i++; continue
        }
        if (inchar) {
            if (esc) esc = 0
            else if (c == "\\") esc = 1
            else if (c == "\x27") inchar = 0
            i++; continue
        }
        if (c == "\"") { instr = 1; i++; continue }
        if (c == "\x27") { inchar = 1; i++; continue }
        if (c == "/" && substr(l, i+1, 1) == "/") break
        if (c == "/" && substr(l, i+1, 1) == "*") { inblk = 1; i += 2; continue }
        out = out c
        i++
    }
    return out
}
function brace_delta(s,   a, nb, nc, t, p) {
    a = s; gsub(/[^{}]/, "", a)
    nb = 0; nc = 0
    t = a
    while ((p = index(t, "{")) > 0) { nb++; t = substr(t, p+1) }
    t = a
    while ((p = index(t, "}")) > 0) { nc++; t = substr(t, p+1) }
    return nb - nc
}
function paren_delta(s,   a, nb, nc, t, p) {
    a = s; gsub(/[^()]/, "", a)
    nb = 0; nc = 0
    t = a
    while ((p = index(t, "(")) > 0) { nb++; t = substr(t, p+1) }
    t = a
    while ((p = index(t, ")")) > 0) { nc++; t = substr(t, p+1) }
    return nb - nc
}
function emit_guard() { print "#ifndef QT_NO_OPENGL" }
{
    line = $0

    # --- preprocessor 嵌套跟踪（保证「已在门控内」判定准确） ---
    if (line ~ /^[ \t]*#[ \t]*if/) {
        pp_depth++
        if (index(line, "QT_NO_OPENGL") > 0 && guard_depth == 0) guard_depth = pp_depth
        print line; next
    }
    if (line ~ /^[ \t]*#[ \t]*endif/) {
        if (guard_depth > 0 && pp_depth == guard_depth) guard_depth = 0
        if (pp_depth > 0) pp_depth--
        print line; next
    }
    if (guard_depth > 0) { print line; next }        # 已在门控区内
    if (line ~ /^[ \t]*#/) { print line; next }      # 其他预处理行
    if (line !~ /QOpenGL/) { print line; next }

    code = strip(line)
    if (code ~ /^[ \t]*$/) { print line; next }      # 纯注释行

    ind = ""
    if (match(line, /^[ \t]*/)) ind = substr(line, 1, RLENGTH)

    if (code ~ /^[ \t]*if[ \t]*\(/) {
        # 整块探测：括号归零 + 花括号配对
        buf[1] = line
        nb = 1
        pd = paren_delta(code)
        bd = brace_delta(code)
        done = 0
        if (pd == 0 && bd == 0 && code ~ /;[ \t]*$/) done = 1     # if (x) foo();
        while (!done) {
            if ((getline nxt) <= 0) { manual = 1; man_reason = "unterminated if-block"; break }
            nb++
            buf[nb] = nxt
            if (nxt ~ /^[ \t]*#[ \t]*if/) pp_depth++
            if (nxt ~ /^[ \t]*#[ \t]*endif/ && pp_depth > 0) pp_depth--
            c2 = strip(nxt)
            pd += paren_delta(c2)
            bd += brace_delta(c2)
            if (pd == 0 && bd == 0) done = 1
        }
        if (!manual) {
            emit_guard()
            for (k = 1; k <= nb; k++) print buf[k]
            print "#endif"
            fixed_b++
        } else {
            for (k = 1; k <= nb; k++) print buf[k]
        }
        delete buf
        next
    }

    if (code ~ /;[ \t]*$/) {                          # 单行语句
        emit_guard()
        print line
        print "#endif"
        fixed_c++
        next
    }

    manual = 1
    man_reason = "GL usage is not a self-contained statement (needs manual guard region)"
    print line
}
END {
    exit (manual ? 3 : 0)
}
'

changed_any=0
manual_any=0

for f in $CAND; do
    rel="${f#$SRC/}"
    [ "$rel" = "$f" ] && rel="$(basename "$f")"
    safe="$(echo "$rel" | tr '/' '_')"

    cp "$f" "$WORK/orig/$safe" || { echo "ERROR: cannot back up $f" >&2; exit 1; }

    # FIX-A
    awk "$AWK_INC" "$WORK/orig/$safe" > "$WORK/new/$safe.a"
    awk "$AWK_INC" "$WORK/new/$safe.a" > "$WORK/new/$safe"    # 幂等二次跑（应无变化）
    cmp -s "$WORK/new/$safe.a" "$WORK/new/$safe" || { echo "ERROR: FIX-A not idempotent on $rel" >&2; exit 1; }
    if ! cmp -s "$WORK/orig/$safe" "$WORK/new/$safe"; then
        FIXED_A=$((FIXED_A + 1))
    fi

    # FIX-B / FIX-C
    set +e
    awk -v pp_depth=0 -v guard_depth=0 -v manual=0 \
        "$AWK_STMT" "$WORK/new/$safe" > "$WORK/new/$safe.b" 2>"$WORK/new/$safe.err"
    stmt_rc=$?
    set -e
    [ -s "$WORK/new/$safe.err" ] && cat "$WORK/new/$safe.err" >&2
    if [ "$stmt_rc" -eq 3 ]; then
        manual_any=1
        MANUAL_FILES="$MANUAL_FILES $rel"
    elif [ "$stmt_rc" -ne 0 ]; then
        echo "ERROR: FIX-B/C failed on $rel (rc=$stmt_rc)" >&2
        exit 1
    fi
    mv "$WORK/new/$safe.b" "$WORK/new/$safe"

    if ! cmp -s "$WORK/orig/$safe" "$WORK/new/$safe"; then
        changed_any=1
        CHANGED_FILES="$CHANGED_FILES $rel"
        if [ "$DRY" -eq 0 ]; then
            cp "$WORK/new/$safe" "$f" || { echo "ERROR: cannot write $f" >&2; exit 1; }
        fi
    fi
done

# ---------- 补丁导出 ----------
if [ -n "$PATCH_OUT" ] && [ "$changed_any" -eq 1 ] && [ "$DRY" -eq 0 ]; then
    : > "$PATCH_OUT"
    for rel in $CHANGED_FILES; do
        safe="$(echo "$rel" | tr '/' '_')"
        [ -f "$WORK/orig/$safe" ] || continue
        {
            echo "diff --git a/$rel b/$rel"
            echo "--- a/$rel"
            echo "+++ b/$rel"
            diff -u "$WORK/orig/$safe" "$WORK/new/$safe" | tail -n +3
        } >> "$PATCH_OUT"
    done
fi

N_CHANGED=0
for _ in $CHANGED_FILES; do N_CHANGED=$((N_CHANGED + 1)); done
N_MANUAL=0
for _ in $MANUAL_FILES; do N_MANUAL=$((N_MANUAL + 1)); done

RC=0
[ "$manual_any" -eq 1 ] && RC=3

if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-NO-OPENGL","changed":%d,"manual":%d,"dry_run":%d,"rc":%d,"files":"%s"}\n' \
        "$N_CHANGED" "$N_MANUAL" "$DRY" "$RC" \
        "$(echo "$CHANGED_FILES" | sed 's/^ *//; s/ /,/g')"
else
    if [ "$N_CHANGED" -eq 0 ]; then
        echo "KB-NO-OPENGL fix: no change needed (already guarded or not GL-affected)"
    else
        echo "KB-NO-OPENGL fix: $N_CHANGED file(s) guarded$([ "$DRY" -eq 1 ] && echo ' [dry-run]')"
        for rel in $CHANGED_FILES; do echo "  + $rel"; done
        [ -n "$PATCH_OUT" ] && [ "$DRY" -eq 0 ] && echo "  patch: $PATCH_OUT"
    fi
    [ "$N_MANUAL" -gt 0 ] && {
        echo "KB-NO-OPENGL fix: MANUAL REVIEW REQUIRED ($N_MANUAL file(s)) — GL usage outside"
        echo "  a self-contained statement cannot be masked mechanically; write an explicit"
        echo "  guard patch for:"
        for rel in $MANUAL_FILES; do echo "    ! $rel"; done
    }
fi

exit "$RC"
