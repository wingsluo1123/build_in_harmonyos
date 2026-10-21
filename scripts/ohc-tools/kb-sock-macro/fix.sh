#!/data/service/hnp/bin/bash
# fix.sh — KB-SOCK-MACRO 修复器：给兼容层兜底定义补 #ifndef 守卫
#
# 处理策略（对应 detect.sh 的通道 A）：
#   原形态：        #define SOCK_CLOEXEC	0
#   修复后：      #ifndef SOCK_CLOEXEC
#                 #define SOCK_CLOEXEC	0
#                 #endif
#   平台已有该宏时，守卫让**系统真值优先**；平台确实没有该宏时，兜底照旧生效
#   （同一份代码在两类系统上都正确，这正是上游应当的写法）。
#
# 与其它策略的取舍：
#   - 不加 -D<MACRO>=<系统值>：把平台细节煮进构建命令，换平台即错，且掩盖缺陷
#   - 不关 -Wmacro-redefined：告警是唯一能在编译期发现"值被覆盖"的信号
#   - 不把兜底值改成系统值：兼容层的意义就是给没有该宏的系统用，写死 Linux 值会错
#
# 用法：
#   fix.sh --src <源码目录> [--cc <编译器>] [--dry-run] [--json]
#   退出码：0=已修复或无需修复  非0=修复失败
#
# 幂等：重复运行安全；只动 #define 兜底行，不碰源码逻辑。
# OHOS aarch64 用 /data/service/hnp/bin/bash。

set -u

SRC=""
CC_BIN="${CC:-/data/service/hnp/bin/clang}"
DRY=0
JSON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --src) SRC="$2"; shift 2 ;;
        --cc) CC_BIN="$2"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
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

WORK="${TMPDIR:-$HOME/tmp}/kb-sock-macro-fix.$$"
mkdir -p "$WORK" || { echo "ERROR: cannot create work dir $WORK" >&2; exit 64; }
trap 'rm -rf "$WORK"' EXIT

# ---------- 目标平台能力对照（只修平台已有、值会被覆盖的宏） ----------
printf '#include <sys/socket.h>\n#include <fcntl.h>\n' > "$WORK/probe.c"
"$CC_BIN" -dM -E "$WORK/probe.c" 2>/dev/null \
    | awk '{ if ($2 ~ /^(SOCK_CLOEXEC|SOCK_NONBLOCK|SOCK_SEQPACKET|MSG_NOSIGNAL|MSG_CMSG_CLOEXEC|SO_REUSEPORT)$/) print $2 "=" $3 }' \
    > "$WORK/defs.txt"

python3 - "$SRC" "$WORK/defs.txt" "$MACROS" "$DRY" "$JSON" <<'PY'
import os, re, sys

src, defs_file, macros_csv, dry, want_json = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1", sys.argv[5] == "1"
macros = set(macros_csv.split())
plat = {}
with open(defs_file, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if "=" in line:
            key, val = line.split("=", 1)
            if key in macros:
                plat[key] = val

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

def_re = re.compile(r"^([ \t]*)#[ \t]*define[ \t]+([A-Za-z_][A-Za-z_0-9]*)")

fixed, skipped_undef = [], []
for path in sorted(files):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines(keepends=True)
    except OSError:
        continue
    guards = {m: re.compile(r"^[ \t]*#[ \t]*ifndef[ \t]+" + re.escape(m) + r"\b") for m in macros}
    out, changed = [], False
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\n")
        match = def_re.match(line)
        if not match:
            out.append(raw)
            continue
        indent, name = match.group(1), match.group(2)
        if name not in macros:
            out.append(raw)
            continue
        if any(guards[name].match(prev.rstrip("\n")) for prev in lines[max(0, idx - 12):idx]):
            out.append(raw)  # 已守卫
            continue
        if name not in plat:
            skipped_undef.append("%s:%d %s" % (path, idx + 1, name))
            out.append(raw)  # 平台没有该宏：兜底合理，保留
            continue
        out.append("%s#ifndef %s\n" % (indent, name))
        out.append(raw)
        out.append("%s#endif\n" % indent)
        fixed.append("%s:%d %s (platform %s, fallback %s)" % (path, idx + 1, name, plat[name], line.split(name, 1)[1].strip()))
        changed = True
    if changed and dry == 0:
        tmp = path + ".kb-tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.writelines(out)
        os.replace(tmp, path)

if want_json:
    print('{"kb":"KB-SOCK-MACRO","fixed":%d,"skipped_plat_undefined":%d,"dry_run":%s}'
          % (len(fixed), len(skipped_undef), "true" if dry else "false"))
else:
    if not fixed:
        print("KB-SOCK-MACRO fix: nothing to do (no unguarded override of platform-defined macro)")
    for item in fixed:
        print("FIX-A: guarded %s" % item)
    for item in skipped_undef:
        print("SKIP: platform does not define %s (upstream fallback is legitimate)" % item)
    if fixed and dry:
        print("KB-SOCK-MACRO fix: dry-run, %d site(s) would be guarded" % len(fixed))
    elif fixed:
        print("KB-SOCK-MACRO fix done: %d site(s) guarded" % len(fixed))
PY

RC=$?
[ "$RC" -eq 0 ] || { echo "ERROR: fix failed (python rc=$RC)" >&2; exit "$RC"; }
exit 0
