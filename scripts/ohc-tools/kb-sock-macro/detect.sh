#!/data/service/hnp/bin/bash
# detect.sh — KB-SOCK-MACRO 检测器：BSD 兼容层兜底定义覆盖 OHOS 已有的 socket 扩展宏
#
# 共性问题（KB-SOCK-MACRO）：
#   BSD 兼容层（bsd-compat/、compat/、portable/ 一类目录）为了老系统会兜底定义
#   socket 扩展位：
#       #ifndef HAVE_SOCK_CLOEXEC
#       #define SOCK_CLOEXEC	0
#       #endif
#   OHOS musl 头（sysroot/usr/include/sys/socket.h）已经提供
#       #define SOCK_CLOEXEC   02000000
#       #define SOCK_NONBLOCK  04000
#   兜底定义与系统定义值不同 → 两个后果：
#     A. 编译期：-Wmacro-redefined（-Werror 下直接红）
#     B. 运行期：宏被覆盖成 0，socket() 的 CLOEXEC/NONBLOCK 位静默丢失
#        （fd 泄漏给 exec 的子进程 / 非阻塞语义消失）
#
# 用法：
#   detect.sh --src <源码目录> [--log <构建日志>] [--cc <编译器>] [--json]
#   退出码：0=未命中  1=命中A（源码无守卫兜底定义）  2=命中B（日志有 macro redefined）  3=同时命中
#
# 判据要点：只有**目标平台已经定义**该宏时才命中——平台确实没有该宏时，
# 上游兜底是合理行为，不算缺陷（避免误报老系统/非 Linux 目标）。
# 本脚本只读，不修改任何文件；OHOS aarch64 用 /data/service/hnp/bin/bash。

set -u

SRC=""
LOGF=""
CC_BIN="${CC:-/data/service/hnp/bin/clang}"
JSON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --src) SRC="$2"; shift 2 ;;
        --log) LOGF="$2"; shift 2 ;;
        --cc) CC_BIN="$2"; shift 2 ;;
        --json) JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

[ -z "$SRC" ] && { echo "ERROR: --src required" >&2; exit 64; }
[ -d "$SRC" ] || { echo "ERROR: not a directory: $SRC" >&2; exit 64; }
command -v "$CC_BIN" >/dev/null 2>&1 || command -v clang >/dev/null 2>&1 \
    || { echo "ERROR: no C compiler found (use --cc)" >&2; exit 64; }
command -v "$CC_BIN" >/dev/null 2>&1 || CC_BIN="clang"

MACROS="SOCK_CLOEXEC SOCK_NONBLOCK SOCK_SEQPACKET MSG_NOSIGNAL MSG_CMSG_CLOEXEC SO_REUSEPORT"

WORK="${TMPDIR:-$HOME/tmp}/kb-sock-macro-detect.$$"
mkdir -p "$WORK" || { echo "ERROR: cannot create work dir $WORK" >&2; exit 64; }
trap 'rm -rf "$WORK"' EXIT

# ---------- 通道 C：目标平台能力对照（只读诊断） ----------
PROBE="$WORK/probe.c"
DEFS="$WORK/defs.txt"
printf '#include <sys/socket.h>\n#include <fcntl.h>\n' > "$PROBE"
: > "$DEFS"
"$CC_BIN" -dM -E "$PROBE" 2>/dev/null \
    | awk '{ if ($2 ~ /^(SOCK_CLOEXEC|SOCK_NONBLOCK|SOCK_SEQPACKET|MSG_NOSIGNAL|MSG_CMSG_CLOEXEC|SO_REUSEPORT)$/) print $2 "=" $3 }' \
    > "$DEFS"

# ---------- 通道 A：源码扫描（未加 #ifndef 守卫的兜底定义） ----------
SCAN="$WORK/hits.txt"
python3 - "$SRC" "$DEFS" "$MACROS" > "$SCAN" 2>"$WORK/scan.err" <<'PY'
import os, re, sys

src, defs_file, macros_csv = sys.argv[1], sys.argv[2], sys.argv[3]
macros = set(macros_csv.split())
plat = {}
with open(defs_file, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            if k in macros:
                plat[k] = v

EXT = (".h", ".hh", ".hpp", ".hxx", ".c", ".cc", ".cpp", ".cxx")
SKIP = {".git", "build", "_build", "node_modules", "__pycache__", ".cache"}
MAXDEPTH = 8

files = []
for root, dirs, names in os.walk(src):
    if root[len(src):].count(os.sep) >= MAXDEPTH:
        dirs[:] = []
    dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
    for name in names:
        if name.endswith(EXT):
            files.append(os.path.join(root, name))

def_re = re.compile(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_][A-Za-z_0-9]*)")

for path in sorted(files):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        continue
    guard = {m: re.compile(r"^[ \t]*#[ \t]*ifndef[ \t]+" + re.escape(m) + r"\b") for m in macros}
    for idx, line in enumerate(lines):
        match = def_re.match(line)
        if not match:
            continue
        name = match.group(1)
        if name not in macros:
            continue
        if any(guard[name].match(prev) for prev in lines[max(0, idx - 12):idx]):
            continue  # 已有守卫，正确形态
        value = plat.get(name)
        if value is None:
            # 平台确实没有这个宏：上游兜底合理，不命中
            print("INFO\t%s:%d\t%s\t#platform-undefined" % (path, idx + 1, name))
            continue
        print("HIT\t%s:%d\t%s\t%s\t%s" % (path, idx + 1, name, value, line.strip()))
PY

HIT_A=0
DETAIL_A=""
while IFS="$(printf '\t')" read -r kind loc macro platval text; do
    [ "$kind" = "HIT" ] || continue
    HIT_A=$((HIT_A + 1))
    DETAIL_A="${DETAIL_A}${loc} ${macro}: platform ${platval} overridden by ${text#*define }; "
done < "$SCAN"
DETAIL_A="${DETAIL_A%; }"

# ---------- 通道 B：构建日志特征 ----------
HIT_B=0
DETAIL_B=""
if [ -n "$LOGF" ] && [ -f "$LOGF" ]; then
    HIT_B_LINES="$(grep -nE "'(SOCK_CLOEXEC|SOCK_NONBLOCK|SOCK_SEQPACKET|MSG_NOSIGNAL|MSG_CMSG_CLOEXEC|SO_REUSEPORT)' macro redefined|redefinition of '(SOCK_CLOEXEC|SOCK_NONBLOCK|SOCK_SEQPACKET|MSG_NOSIGNAL|MSG_CMSG_CLOEXEC|SO_REUSEPORT)'" "$LOGF" 2>/dev/null)"
    if [ -n "$HIT_B_LINES" ]; then
        HIT_B=1
        DETAIL_B="log: $(printf '%s' "$HIT_B_LINES" | wc -l | tr -d ' ') macro-redefined line(s) for socket extension macros"
    fi
fi

RC=$(( HIT_A > 0 ? 1 : 0 ))
[ "$HIT_B" -eq 1 ] && RC=$((RC + 2))

PLAT_TABLE="$(tr '\n' ' ' < "$DEFS")"
if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-SOCK-MACRO","hit_a":%d,"hit_b":%d,"rc":%d,"detail_a":"%s","detail_b":"%s","platform":"%s"}\n' \
        "$HIT_A" "$HIT_B" "$RC" "$DETAIL_A" "$DETAIL_B" "$PLAT_TABLE"
else
    if [ "$RC" -eq 0 ]; then
        echo "KB-SOCK-MACRO: no hit (no unguarded socket-extension fallback overriding platform values)"
        echo "platform: ${PLAT_TABLE:-<none of the target macros are defined>}"
    else
        [ "$HIT_A" -gt 0 ] && echo "KB-SOCK-MACRO HIT-A ($HIT_A): $DETAIL_A"
        [ "$HIT_B" -eq 1 ] && echo "KB-SOCK-MACRO HIT-B: $DETAIL_B"
        echo "platform: ${PLAT_TABLE:-<none>}"
        echo "fix:   bash $(dirname "$0")/fix.sh --src $SRC --cc $CC_BIN"
    fi
    # 平台确实缺宏的情况单独提示，避免把合理兜底当缺陷
    grep -q '^INFO' "$SCAN" 2>/dev/null \
        && echo "note: upstream fallback kept for macros the target does not define: $(grep -c '^INFO' "$SCAN") site(s)"
fi
exit "$RC"
