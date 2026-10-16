#!/usr/bin/env bash
# test_xhk_consumer.sh — xhk 1.2 鸿蒙消费者端到端用例（rule12 消费者用例）
#
# 与 test_xhk.sh（确定性 CLI 断言 + ELF 平台属性）不同，本脚本给出**完整消费者
# 用例**：把被测包打包出来的 bin/xhk 当成最终用户手中的命令行工具来用，让它在
# 一台真实运行的 X server 上跑通 xhk 的核心业务工作流，并对**业务输出**做断言。
#
# xhk 的业务工作流（上游 src/xhk.c）：
#   空格键作为修饰键——单独的 Space 原样透传；Space 按住后再按某一侧的键，该键被
#   镜像到键盘另一半（mirror_key() 的 keycode 折叠 + Backspace/Tab、Enter/Caps、
#   -/_ 特例对调；ProcessKeycode() 的三态机 Start/Pressed/Modified），最终经
#   XTest 真注入 X server。`xhk -t` 是上游内置的功能自检，逐条驱动上述状态机并
#   比对 keycode/状态（含「Space+F 必须变成 J」这类镜像断言）。它必须真连上
#   X server 才可能执行：
#     - 无 X server 时 construct() 返回 NULL 而调用点解引用 → SIGSEGV（实测
#       rc=139，上游 aarch64 缺陷 2，见 notes.md）——因此本用例「通过」不可能来自
#       空跑：要拿到 rc=0 与 0 errors，必须真的连上 server 并跑完状态机；
#     - 连上后 KeycodeTest() 逐条比对 ProcessKeycode() 的返回 keycode 与状态，
#       任一条不符即打印 "returned ... but expected ..." 并计入 errors。
#
# 鸿蒙消费者用例清单：
#   HC-1 半键盘镜像工作流端到端：真实执行打包的 bin/xhk -dd -t，断言
#        (a) 真的连上了本机 X server（XOpenDisplay / XI Version 2.0）
#        (b) 镜像工作流真的跑到（Verify a key gets mirrored 段落）
#        (c) 状态机真的进入 Modified（镜像态）
#        (d) 状态机经 XTest 真向 X server 注入了按键（Sending keycode ... to XTest）
#        (e) 业务结果：Exiting Test Loop with 0 errors，且全程无 keycode 比对失败
#   HC-2 独立消费者旁路观测：另一个独立 X 客户端（xev）在同一个 X server 上
#        观测被测工具注入的按键事件，断言事件真的由 server 投递给别的客户端
#        （keycode 65 / keysym 0x20 space），证明 HC-1 的注入不是进程内自说自话。
#
# X server 供给顺序：
#   1) 自起一台可控的 Xvfb（PATH → /opt/ohos-guest/bin → /data/service/hnp/bin）：
#      bare server、无 WM，焦点为 PointerRoot，E2E 行为可复现（HC-1 + HC-2 都跑）
#   2) 环境里已可用的 $DISPLAY（同仓库 archives/x/xclip/0.13.1 的既有做法）：
#      跑 HC-1；HC-2 依赖 bare server 的焦点语义，故跳过
#   3) 都没有 → 显式 SKIP（**不计入通过**）并写明平台限制原因后退出 0
# 这样 CI worker 无 X server 时不会把「没跑」记成「通过」，也不会阻塞构建。
#
# 平台限制（规则 7）：OHOS 无 X server，xhk 的运行期功能（XInput2 抓键、XTest
# 注入、setpriority(-20)）在无 X 环境下不可达；本用例在具备 X server 的环境
# （本机 WSL + Xvfb）真实执行并通过，实跑输出与退出码见 notes.md 与 PR 说明。
set -uo pipefail

echo "=== xhk 1.2 HarmonyOS consumer end-to-end cases ==="

pass=0
fail=0
skip=0
ok()      { echo "HC-PASS: $1"; pass=$((pass + 1)); }
bad()     { echo "HC-FAIL: $1"; fail=$((fail + 1)); }
skipped() { echo "HC-SKIP: $1"; skip=$((skip + 1)); }

WORKDIR="$(mktemp -d 2>/dev/null || echo "/tmp/xhk-consumer.$$")"
mkdir -p "$WORKDIR"
XVFB_PID=""
XEV_PID=""
CONTROLLED_SERVER=0
DISPLAY_USED=""

cleanup() {
    [ -n "$XEV_PID" ] && kill "$XEV_PID" 2>/dev/null
    [ -n "$XVFB_PID" ] && kill "$XVFB_PID" 2>/dev/null
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

count_of() {   # $1=file $2=固定串
    local n
    n="$(grep -cF -- "$2" "$1" 2>/dev/null)" || n=0
    printf '%s' "${n:-0}"
}

# ── 被测产物 ───────────────────────────────────────────────────────────
BIN="$(command -v xhk || true)"
if [ -z "$BIN" ]; then
    echo "HC-FAIL: xhk not on PATH (conanrun did not inject package bin/)"
    printf 'HMBS_HARMONY_CONSUMER_RESULT={"executed":false,"passed":false,"reason":"xhk not on PATH"}\n'
    exit 1
fi
echo "consumer target: $BIN"

# 本地/CI 模拟运行环境（/opt/ohos-guest，stock musl）缺 OHOS 硬化符号
# __fd_chk / arc4random_buf，制品仓 X11 二进制需要 shim；真机 libc 自带，shim
# 不存在时自动跳过。LD_PRELOAD 只经 env 传给被测 aarch64 进程。
PRELOAD=""
for s in /opt/ohos-guest/lib/libfdchkshim.so /opt/ohos-guest/lib/libarc4shim.so; do
    [ -f "$s" ] && PRELOAD="${PRELOAD:+$PRELOAD:}$s"
done

RUN_TIMEOUT=""
command -v timeout >/dev/null 2>&1 && RUN_TIMEOUT="timeout 90"

run_xhk() {
    if [ -n "$RUN_TIMEOUT" ]; then
        $RUN_TIMEOUT env LD_PRELOAD="$PRELOAD" DISPLAY="$DISPLAY_USED" "$BIN" "$@"
    else
        env LD_PRELOAD="$PRELOAD" DISPLAY="$DISPLAY_USED" "$BIN" "$@"
    fi
}

# 只保留被测进程自己的输出，滤掉 host 侧 ld.so 对 aarch64 shim 的噪声告警
strip_host_noise() { grep -v 'cannot be preloaded' "$1" 2>/dev/null || true; }

# ── X server 供给 ──────────────────────────────────────────────────────
display_num_of() {
    case "$1" in
        *:*) printf '%s' "${1#*:}" | sed 's/\..*$//' ;;
        *) printf '' ;;
    esac
}

tcp_port_open() {
    # bash /dev/tcp 探测；宿主 shell 不支持时返回非 0（由调用方兜底）
    (exec 3<>"/dev/tcp/$1/$2") >/dev/null 2>&1
}

display_reachable() {
    local d num host
    d="$1"
    num="$(display_num_of "$d")"
    [ -z "$num" ] && return 1
    host="${d%%:*}"
    if [ -z "$host" ]; then
        [ -S "/tmp/.X11-unix/X$num" ] && return 0
        host=127.0.0.1
    fi
    tcp_port_open "$host" "$((6000 + num))"
}

find_xvfb() {
    local c
    for c in "$(command -v Xvfb 2>/dev/null || true)" \
             /opt/ohos-guest/bin/Xvfb \
             /data/service/hnp/bin/Xvfb; do
        if [ -n "$c" ] && [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
    done
    return 1
}

start_xvfb() {
    local xvfb n
    xvfb="$(find_xvfb)" || return 1
    for n in 99 98 97 96 95 94 93 92; do
        [ -e "/tmp/.X${n}-lock" ] && continue
        display_reachable ":$n" >/dev/null 2>&1 && continue
        : > "$WORKDIR/xvfb.log"
        "$xvfb" ":$n" -screen 0 800x600x24 -ac -nolisten unix -listen tcp \
            >"$WORKDIR/xvfb.log" 2>&1 &
        XVFB_PID=$!
        # 等 server 起来（最长 15s）
        i=0
        while [ "$i" -lt 15 ]; do
            display_reachable "127.0.0.1:$n" && break
            kill -0 "$XVFB_PID" 2>/dev/null || break
            sleep 1
            i=$((i + 1))
        done
        # Xvfb 在 display 已被占用时会立刻退出；进程仍存活即已接管该 display
        if kill -0 "$XVFB_PID" 2>/dev/null; then
            DISPLAY_USED="127.0.0.1:$n"
            CONTROLLED_SERVER=1
            echo "X server: $xvfb :$n (started by this test, TCP, pid $XVFB_PID)"
            return 0
        fi
        XVFB_PID=""
        sleep 1
    done
    echo "X server: Xvfb found but could not be started on displays 99..92:"
    tail -3 "$WORKDIR/xvfb.log" 2>/dev/null | sed 's/^/    /'
    return 1
}

provision_display() {
    start_xvfb && return 0
    if [ -n "${DISPLAY:-}" ]; then
        if display_reachable "$DISPLAY"; then
            DISPLAY_USED="$DISPLAY"
            echo "X server: using existing DISPLAY=$DISPLAY (reachable)"
            return 0
        fi
        echo "X server: DISPLAY=$DISPLAY set but not reachable — ignored"
    fi
    return 1
}

if ! provision_display; then
    echo
    echo "HC-SKIP: 无可用 X server（PATH / OHOS guest 下无 Xvfb，且 DISPLAY 不可达）"
    echo "HC-SKIP: HC-1 半键盘镜像工作流 / HC-2 独立旁路观测 按平台限制跳过（不计入通过）"
    echo "HC-SKIP: xhk 运行期功能需真实 X server（OHOS 无 X server，属真机验证范畴）"
    printf 'HMBS_HARMONY_CONSUMER_RESULT={"executed":false,"passed":false,"skipped":2,"reason":"no X server available (no Xvfb, DISPLAY unreachable)"}\n'
    exit 0
fi

# ── HC-2 观测器先起（观测 HC-1 的同一次真实执行）────────────────────────
XEV_LOG="$WORKDIR/xev.log"
: > "$XEV_LOG"
OBSERVER=""
OBSERVER_REASON=""
if [ "$CONTROLLED_SERVER" -ne 1 ]; then
    OBSERVER_REASON="HC-2 needs a bare X server started by this test (an existing DISPLAY may have a WM and non-PointerRoot focus)"
elif ! command -v xev >/dev/null 2>&1; then
    OBSERVER_REASON="xev not installed"
else
    # bare Xvfb：无 WM，焦点为 PointerRoot；铺满指针所在区域的窗口即可收到注入按键。
    # 起 xev 最多试 3 次（server 刚起来时可能还没准备好）。
    attempt=0
    while [ "$attempt" -lt 3 ]; do
        attempt=$((attempt + 1))
        xev -display "$DISPLAY_USED" -geometry 2000x2000+0+0 >>"$XEV_LOG" 2>&1 &
        XEV_PID=$!
        sleep 3
        if kill -0 "$XEV_PID" 2>/dev/null; then
            OBSERVER="xev"
            echo "HC-2 observer: xev on $DISPLAY_USED (pid $XEV_PID, attempt $attempt)"
            break
        fi
        XEV_PID=""
        sleep 2
    done
    if [ -z "$OBSERVER" ]; then
        OBSERVER_REASON="xev failed to start on $DISPLAY_USED"
        echo "HC-2 observer: xev failed to start — last lines of its output:"
        tail -5 "$XEV_LOG" 2>/dev/null | sed 's/^/    | /'
    fi
fi
OBS_BEFORE="$(count_of "$XEV_LOG" 'KeyPress event')"

# ── HC-1 半键盘镜像工作流（真实执行打包产物）────────────────────────────
OUT="$WORKDIR/xhk_t.out"
echo
echo "HC-1 run: xhk -dd -t   (DISPLAY=$DISPLAY_USED)"
run_xhk -dd -t >"$OUT" 2>&1
HC1_RC=$?
strip_host_noise "$OUT" | sed 's/^/    | /'

hc1_transcript="$(strip_host_noise "$OUT")"
hc1_check() {   # $1=描述 $2=固定串
    if printf '%s\n' "$hc1_transcript" | grep -qF -- "$2"; then
        ok "HC-1 $1"
    else
        bad "HC-1 $1 (missing: $2)"
    fi
}

if [ "$HC1_RC" -eq 0 ]; then
    ok "HC-1 product exited 0 on a live X server"
else
    bad "HC-1 product exit code = $HC1_RC (expected 0; 139 would mean it never reached the X server)"
fi
hc1_check "connected to the X server it was pointed at" "XOpenDisplay(\"$DISPLAY_USED\")"
hc1_check "XInput2 negotiated with the live server" "XI Version 2.0"
hc1_check "mirror workflow executed" "Verify a key gets mirrored"
hc1_check "state machine entered Modified (mirror) state" "Entering ProcessKeycode in state Modified"
hc1_check "state machine injected a key press through XTest" "Sending keycode Down 65, (space) to XTest"
hc1_check "state machine injected a key release through XTest" "Sending keycode Up 65, (space) to XTest"
hc1_check "business result: Exiting Test Loop with 0 errors" "Exiting Test Loop with 0 errors"

if printf '%s\n' "$hc1_transcript" | grep -qF 'but expected'; then
    bad "HC-1 the product reported a keycode/state mismatch: $(printf '%s\n' "$hc1_transcript" | grep -F 'but expected' | head -2 | tr '\n' ' ')"
else
    ok "HC-1 no keycode/state mismatch in the product's own comparison output"
fi
if printf '%s\n' "$hc1_transcript" | grep -qF "Couldn't connect to XServer"; then
    bad "HC-1 the product reported it could not connect to the X server"
else
    ok "HC-1 the product did not report an X connection failure"
fi

# ── HC-2 独立消费者旁路观测 ────────────────────────────────────────────
echo
HC1_FAILS=$fail
if [ -z "$OBSERVER" ]; then
    skipped "HC-2 independent observer unavailable (${OBSERVER_REASON:-unknown reason}) — not counted as pass"
else
    sleep 2
    OBS_AFTER="$(count_of "$XEV_LOG" 'KeyPress event')"
    SPACE_SEEN="$(count_of "$XEV_LOG" 'keycode 65 (keysym 0x20, space)')"
    echo "HC-2 observer: space KeyPress before=$OBS_BEFORE after=$OBS_AFTER, matching lines=$SPACE_SEEN"
    grep -F 'keycode 65 (keysym 0x20, space)' "$XEV_LOG" 2>/dev/null | head -2 | sed 's/^/    | /'
    if [ "$OBS_AFTER" -gt "$OBS_BEFORE" ] && [ "${SPACE_SEEN:-0}" -gt 0 ]; then
        ok "HC-2 an independent X client received the key events the packaged product injected into the server"
    else
        bad "HC-2 independent X client observed no injected key event (before=$OBS_BEFORE after=$OBS_AFTER)"
    fi
    if [ "${SPACE_SEEN:-0}" -gt 0 ]; then
        ok "HC-2 observed keycode/keysym match the injected key (keycode 65 / keysym 0x20 space)"
    else
        bad "HC-2 observed no space keysym (expected keycode 65 / keysym 0x20)"
    fi
fi

# ── 小结 ───────────────────────────────────────────────────────────────
HC2_FAILS=$((fail - HC1_FAILS))
HC1_STATUS='pass'
[ "$HC1_FAILS" -ne 0 ] && HC1_STATUS='fail'
HC2_STATUS='skipped'
if [ -n "$OBSERVER" ]; then
    HC2_STATUS='pass'
    [ "$HC2_FAILS" -ne 0 ] && HC2_STATUS='fail'
fi
[ "$CONTROLLED_SERVER" -eq 1 ] && echo "X server: started by this test (Xvfb $DISPLAY_USED), stopped on exit"

echo "test xhk 1.2 consumer cases: ${pass} passed, ${fail} failed, ${skip} skipped"
printf 'HMBS_HARMONY_CONSUMER_CASES={"HC-1":"%s","HC-2":"%s"}\n' "$HC1_STATUS" "$HC2_STATUS"
printf 'HMBS_HARMONY_CONSUMER_RESULT={"executed":true,"passed":%s,"passedCount":%d,"failedCount":%d,"skippedCount":%d,"command":"test_xhk_consumer.sh","cases":["HC-1","HC-2"]}\n' \
    "$([ "$fail" -eq 0 ] && echo true || echo false)" "$pass" "$fail" "$skip"

[ "$fail" -eq 0 ]
