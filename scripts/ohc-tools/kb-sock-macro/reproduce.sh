#!/data/service/hnp/bin/bash
# reproduce.sh — KB-SOCK-MACRO 复现脚本：样例库（sockcloexec-demo）两阶段对照
#
# 阶段① 不启用 SKILL：直接编译样例库
#   - 宽松编译（-Wall）：编译通过，只有 -Wmacro-redefined 告警
#   - 运行消费者断言：socket() 成功但 FD_CLOEXEC / O_NONBLOCK 未生效 → 失败
#   - 严格编译（-Werror=macro-redefined）：直接报错（多数项目与发行构建的实际口径）
# 阶段② 启用 SKILL：detect -> fix -> 严格编译通过 + 消费者断言全绿
#
# ⚠ SIGPIPE 规避铁律：
#   - 所有命令输出重定向到日志文件，绝不 `cmd | head`（SIGPIPE 会杀掉整条管道，
#     掩盖真实退出码）
#   - 退出码从 $? 与日志文件采集，不在管道里判
#
# 用法：reproduce.sh [--sample <目录>] [--cc <编译器>] [--keep] [--json]
#   --sample  样例库目录（默认本目录 sample/sockcloexec-demo，可用 KB_SOCK_MACRO_SAMPLE 覆盖）
#   --cc      编译器（默认 $CC，否则项目工具链 /data/service/hnp/bin/clang）
#   --keep    保留工作目录（默认结束清理）
#   --json    机器可读摘要输出到 stdout
#
# 退出码：0=两阶段都符合预期（OFF 复现 / ON 通过）  1=ON 阶段未通过  2=OFF 阶段未复现
# 本脚本不写死任何本地缓存路径；工作目录取 $TMPDIR 或 $HOME/tmp。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="${TMPDIR:-$HOME/tmp}/kb-sock-macro-repro.$$"
SAMPLE=""
CC_BIN="${CC:-/data/service/hnp/bin/clang}"
KEEP=0
JSON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --sample) SAMPLE="$2"; shift 2 ;;
        --cc) CC_BIN="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --json) JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

command -v "$CC_BIN" >/dev/null 2>&1 || command -v clang >/dev/null 2>&1 \
    || { echo "ERROR: no C compiler found (use --cc)" >&2; exit 64; }
command -v "$CC_BIN" >/dev/null 2>&1 || CC_BIN="clang"

[ -z "$SAMPLE" ] && SAMPLE="${KB_SOCK_MACRO_SAMPLE:-$SCRIPT_DIR/sample/sockcloexec-demo}"
[ -d "$SAMPLE" ] || { echo "ERROR: sample dir not found: $SAMPLE" >&2; exit 64; }

LOG="$WORK/repro.log"
mkdir -p "$WORK" || { echo "ERROR: cannot create $WORK" >&2; exit 64; }
: > "$LOG"
cleanup() { [ "$KEEP" -eq 1 ] || rm -rf "$WORK"; }
trap cleanup EXIT

say() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }
say "compiler: $CC_BIN ($("$CC_BIN" --version 2>/dev/null | sed -n 1p))"
say "sample: $SAMPLE"
say "work: $WORK"

CFLAGS_COMMON="-I$SAMPLE/include -I$SAMPLE -O2 -Wall"
STRICT_FLAGS="-Werror=macro-redefined"

# ---------- 阶段①：不启用 SKILL ----------
P1="$WORK/phase1"
cp -r "$SAMPLE" "$P1"
P1_LOOSE_BUILD="$WORK/p1-loose-build.log"
P1_LOOSE_RUN="$WORK/p1-loose-run.log"
P1_STRICT="$WORK/p1-strict-build.log"

(
    cd "$P1" || exit 1
    "$CC_BIN" $CFLAGS_COMMON src/demo_sock.c test/check_cloexec.c -o check_loose
) > "$P1_LOOSE_BUILD" 2>&1
P1_LOOSE_RC=$?
say "phase1 loose build rc=$P1_LOOSE_RC"

P1_RUN_RC=""
if [ "$P1_LOOSE_RC" -eq 0 ]; then
    ( cd "$P1" && ./check_loose ) > "$P1_LOOSE_RUN" 2>&1 </dev/null
    P1_RUN_RC=$?
    say "phase1 loose run rc=$P1_RUN_RC"
else
    say "phase1 loose build failed (unexpected: replica should compile with warnings only)"
fi

(
    cd "$P1" || exit 1
    "$CC_BIN" $CFLAGS_COMMON $STRICT_FLAGS src/demo_sock.c test/check_cloexec.c -o check_strict
) > "$P1_STRICT" 2>&1
P1_STRICT_RC=$?
say "phase1 strict build rc=$P1_STRICT_RC"

P1_WARN=$(grep -c "macro redefined" "$P1_LOOSE_BUILD" 2>/dev/null || true)
P1_NOTOK=$(grep -c "^not ok" "$P1_LOOSE_RUN" 2>/dev/null || true)
P1_WARN=${P1_WARN:-0}; P1_NOTOK=${P1_NOTOK:-0}
say "phase1: warnings=$P1_WARN failed_assertions=$P1_NOTOK"

if [ "$P1_LOOSE_RC" -eq 0 ] && [ "$P1_RUN_RC" -ne 0 ] && [ "$P1_NOTOK" -ge 1 ] && [ "$P1_STRICT_RC" -ne 0 ]; then
    P1_VERDICT="reproduced"
    say "PASS: phase1 reproduced (semantic defect + strict build failure)"
else
    P1_VERDICT="not-reproduced"
    say "FAIL: phase1 did not reproduce the documented failure modes"
fi

# ---------- 阶段②：启用 SKILL（detect -> fix -> 严格编译 -> 断言） ----------
P2="$WORK/phase2"
cp -r "$SAMPLE" "$P2"
P2_DETECT="$WORK/p2-detect.log"
P2_FIX="$WORK/p2-fix.log"
P2_BUILD="$WORK/p2-strict-build.log"
P2_RUN="$WORK/p2-run.log"

"$SCRIPT_DIR/detect.sh" --src "$P2" --cc "$CC_BIN" > "$P2_DETECT" 2>&1
DETECT_RC=$?
say "phase2 detect rc=$DETECT_RC"

"$SCRIPT_DIR/fix.sh" --src "$P2" --cc "$CC_BIN" > "$P2_FIX" 2>&1
FIX_RC=$?
say "phase2 fix rc=$FIX_RC"

if [ "$DETECT_RC" -eq 0 ]; then
    say "FAIL: detect found nothing on the defective sample"
    P2_VERDICT="detect-no-hit"
elif [ "$FIX_RC" -ne 0 ]; then
    say "FAIL: fix.sh rc=$FIX_RC"
    P2_VERDICT="fix-failed"
else
    (
        cd "$P2" || exit 1
        "$CC_BIN" -Iinclude -I. -O2 -Wall $STRICT_FLAGS src/demo_sock.c test/check_cloexec.c -o check_fixed
    ) > "$P2_BUILD" 2>&1
    P2_BUILD_RC=$?
    say "phase2 strict build rc=$P2_BUILD_RC"
    if [ "$P2_BUILD_RC" -ne 0 ]; then
        P2_VERDICT="build-failed"
    else
        ( cd "$P2" && ./check_fixed ) > "$P2_RUN" 2>&1 </dev/null
        P2_RUN_RC=$?
        P2_NOTOK=$(grep -c "^not ok" "$P2_RUN" 2>/dev/null || true)
        P2_NOTOK=${P2_NOTOK:-0}
        say "phase2 run rc=$P2_RUN_RC not_ok=$P2_NOTOK"
        if [ "$P2_RUN_RC" -eq 0 ] && [ "$P2_NOTOK" -eq 0 ]; then
            P2_VERDICT="fixed"
        else
            P2_VERDICT="assertions-failed"
        fi
    fi
fi

say "===== SUMMARY ====="
say "phase1=$P1_VERDICT phase2=$P2_VERDICT"
say "logs: $P1_LOOSE_BUILD $P1_LOOSE_RUN $P1_STRICT $P2_DETECT $P2_FIX $P2_BUILD $P2_RUN"

if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-SOCK-MACRO","sample":"%s","phase1":"%s","phase2":"%s","phase1_warnings":%s,"phase1_failed_assertions":%s,"log":"%s"}\n' \
        "$(basename "$SAMPLE")" "$P1_VERDICT" "$P2_VERDICT" "${P1_WARN:-0}" "${P1_NOTOK:-0}" "$LOG"
else
    echo "===== KB-SOCK-MACRO reproduce summary ====="
    echo "phase1 (no skill):   $P1_VERDICT  (warnings=$P1_WARN, failed_assertions=$P1_NOTOK, strict_build_rc=$P1_STRICT_RC)"
    echo "phase2 (with skill): $P2_VERDICT"
    echo "full log: $LOG"
    if [ "$KEEP" -eq 1 ]; then
        echo "phase1 strict build error:"
        sed -n '1,12p' "$P1_STRICT"
        echo "phase1 runtime assertions:"
        sed -n '1,10p' "$P1_LOOSE_RUN"
    fi
fi

if [ "$P1_VERDICT" = "reproduced" ] && [ "$P2_VERDICT" = "fixed" ]; then
    exit 0
fi
[ "$P1_VERDICT" = "reproduced" ] || exit 2
exit 1
