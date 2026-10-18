#!/bin/sh
# test_wmjupiter.sh — 真实执行打包后的 wmJupiter 二进制（消费者视角，R34）
#
# 用法: sh test_wmjupiter.sh <包内 bin/wmJupiter 的绝对路径>
#
# 上游不提供测试套件（tag 归档仅 9 个条目；Makefile 只有 all/install 目标），
# 故本脚本以「消费者用例」形式驱动交付物本身。共两类：
#
#   A 类  失败路径（无需 display 即可稳定判定）
#     1. wmJupiter -display :<N>
#        initXwindow() 的 argv 扫描循环取出 `-display` 的值 → XDisplayName(":N")
#        → XOpenDisplay(":N") 失败 → stderr 打印
#        "<argv0>: can't open display :N" → exit(1)
#        N 由本脚本按 PID 分散取（300 段 = TCP 6300-6399），与本脚本对端自用的
#        20-219 段（6020-6219）不相交：显示号一旦写死，若该号上残留着监听
#        （实测本机 :99/TCP 6099 就被占住过），客户端会连上并一直等 setup 应答，
#        用例就退化成「有人在假装 X server」，只能靠上界超时收场。
#     2. wmJupiter（无参，DISPLAY 未设置）走同一条错误分支。
#     这两条同时覆盖动态链接：产物 NEEDED 含 libXpm.so.4 / libX11.so.6 /
#     libXext.so.6，任一缺失都会在 main 之前由 loader 报
#     "error while loading shared libraries"。
#
#   B 类  完整消费者用例：headless X11 协议对端端到端（本例即 rule12 所指
#        「真正跑通功能/流程的端到端用例」，按四段式说明）
#
#     · 构造输入：x11_headless.py 在 127.0.0.1:60xx 起一个 X11 显示对端
#       （纯 Python stdlib，按 xcb/libX11 权威线格式实现连接握手、请求解析与
#       应答），并以 DISPLAY 指向它；对端在累计 60 次「拷贝到窗口」后注入一个
#       BadImplementation 协议错误并关闭连接，作为可判定的终止信号。
#       不用 Xvfb、不设 DISPLAY=:0、不 dlopen（E530 明确禁止的三条路线）。
#     · 真实执行：运行打包产物 wmJupiter -22，它按自身代码路径依次执行
#       XOpenDisplay → 读 Root 的 colormap → 分配 XPM 的 10 种颜色 →
#       XpmCreatePixmapFromData（134x148）→ XCreateSimpleWindow ×2（64x64）→
#       XCreateBitmapFromData + ShapeMask（形状遮罩）→ 设 5 条 WM 属性 →
#       XMapWindow → 进入 XCopyArea 动画循环。
#     · 产出结果：对端按协议**真实累积**的服务端状态——窗口/位图几何与深度、
#       PutImage 解码出的像素颜色、收到的属性内容、ShapeMask 计数、拷贝帧数；
#       外加客户端进程的退出码与 stderr。
#     · 校验内容：脚本逐项断言上述服务端状态（见 B2-B8），即校验「程序真的把
#       画面画进了 X server」而不是脚本回显；对端自身状态仅由它据实记录，
#       不做任何回填。
#
# 不用 set -eu（同 xeyes/xidle/wmcalc 已过门禁口径），自行统计通过/失败。

BIN="$1"
HERE=$(cd "$(dirname "$0")" && pwd)

# 临时工作目录（对端报告 / 客户端输出）须在 A 类用例之前就绪：
# A 类负路径同样要「带时长上界地运行二进制」，否则客户端一旦卡住会把整个 W3/CI 拖到超时
TMPD=${TMPDIR:-/tmp}
KEEP_WORK=""
if [ -n "$WMJUPITER_TEST_WORK" ]; then
    # 排障用：指定固定工作目录并保留中间产物（对端报告/客户端输出）
    WORK="$WMJUPITER_TEST_WORK"
    KEEP_WORK=1
else
    WORK="$TMPD/wmjupiter-test-$$"
fi
if mkdir -p "$WORK" 2>/dev/null; then
    :
else
    WORK="$HERE"
    KEEP_WORK=1
fi
REPORT="$WORK/peer-report.txt"
RUN_OUT="$WORK/client-out.txt"
rm -f "$REPORT" "$RUN_OUT"

# count_match() 按换行切分报告全文，关掉 glob 防止行内 */? 被展开成文件名
set -f

pass=0
fail=0

ok() {
    pass=$((pass + 1))
    echo "  ok   - $1"
}

bad() {
    fail=$((fail + 1))
    echo "  FAIL - $1"
}

# 纯 shell 逐行匹配（$REP 为对端报告全文）
# 不用 grep -o：CI 的最小 PATH 下由另一 grep 实现承担，会静默返回空
count_match() {
    MC=0
    ML=""
    _saved=$IFS
    IFS='
'
    for _l in $REP; do
        case "$_l" in
            *"$1"*)
                MC=$((MC + 1))
                if [ -z "$ML" ]; then
                    ML="$_l"
                fi
                ;;
        esac
    done
    IFS=$_saved
}

# 受限时长运行命令：$1 秒数，其余为命令；输出写入 $RUN_OUT，退出码写入 $RUN_RC
# （不依赖 timeout(1)，POSIX sh 后台作业 + wait 取真实退出码）
run_bounded() {
    _secs=$1
    shift
    "$@" > "$RUN_OUT" 2>&1 &
    _pid=$!
    _i=0
    while [ "$_i" -lt "$_secs" ]; do
        if ! kill -0 "$_pid" 2>/dev/null; then
            break
        fi
        sleep 1
        _i=$((_i + 1))
    done
    if kill -0 "$_pid" 2>/dev/null; then
        kill "$_pid" 2>/dev/null
        sleep 1
        kill -9 "$_pid" 2>/dev/null
        RUN_RC=124
    else
        wait "$_pid"
        RUN_RC=$?
    fi
}

echo "== wmjupiter test_package =="
echo "binary: $BIN"

# --- A1: 交付物存在且非空 ------------------------------------------------
if [ -f "$BIN" ] && [ -s "$BIN" ]; then
    ok "包内 bin/wmJupiter 存在且非空"
else
    bad "包内 bin/wmJupiter 缺失或为空"
    echo "RESULT: $pass passed, $fail failed"
    exit 1
fi

# --- A2-A4: 指定 display 但无 X server → 走 XOpenDisplay 失败分支 --------
# display 号不能写死：若该号上残留了监听（实测本机 :99 = TCP 6099 被占），
# 客户端会连上并在 XOpenDisplay 里等 setup 应答，直到上界超时——那时用例测到的
# 不是「没有 X server」而是「有人在假装 X server」。
# 这里按 PID 取 300 段（端口 6300-6399），与对端自己用的 20-219 段（6020-6219）
# 完全不相交，故本脚本历次运行遗留的对端不可能毒化它；60s 上界继续保留兜底。
NEG_N=$(( ($$ % 100) + 300 ))
run_bounded 60 "$BIN" -display ":$NEG_N"
out=$(cat "$RUN_OUT" 2>/dev/null)
rc=$RUN_RC

if [ "$rc" -eq 1 ]; then
    ok "wmJupiter -display :$NEG_N 退出码为 1（initXwindow 的 exit(1) 分支）"
else
    bad "wmJupiter -display :$NEG_N 退出码应为 1，实测 $rc（输出: $out）"
fi

case "$out" in
    *"can't open display"*)
        ok "stderr 含上游固定短语 \"can't open display\"（initXwindow 错误分支真实执行）"
        ;;
    *)
        bad "stderr 未出现 \"can't open display\"（输出: $out）"
        ;;
esac

case "$out" in
    *":$NEG_N"*)
        ok "stderr 原样回显 \":$NEG_N\"（-display 参数扫描 + XDisplayName 真实生效）"
        ;;
    *)
        bad "stderr 未回显 \":$NEG_N\"（输出: $out）"
        ;;
esac

# --- A5: 无 loader 报错 = libXpm/libX11/libXext 全部解析成功 --------------
case "$out" in
    *"shared libraries"* | *"cannot open shared object"*)
        bad "loader 未能解析共享库（libXpm/libX11/libXext 链接不完整）: $out"
        ;;
    *)
        ok "无 loader 报错（NEEDED 的 libXpm.so.4/libX11.so.6/libXext.so.6 均已解析）"
        ;;
esac

# --- A6: 无参形态走同一条失败分支 ----------------------------------------
unset DISPLAY
run_bounded 60 "$BIN"
out2=$(cat "$RUN_OUT" 2>/dev/null)
rc2=$RUN_RC

if [ "$rc2" -eq 1 ]; then
    ok "wmJupiter（无参，DISPLAY 未设置）退出码为 1"
else
    bad "wmJupiter（无参）退出码应为 1，实测 $rc2（输出: $out2）"
fi

case "$out2" in
    *"can't open display"*)
        ok "无参形态同样打印 \"can't open display\"（默认 display 查找路径真实执行）"
        ;;
    *)
        bad "无参形态未打印 \"can't open display\"（输出: $out2）"
        ;;
esac

# =========================================================================
# B 类：headless X11 协议对端端到端消费者用例
# =========================================================================
echo "-- B: headless X11 对端端到端（真实绘制流程）--"

PEER="$HERE/x11_headless.py"
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
        PY=$(command -v "$c")
        break
    fi
done

if [ -f "$PEER" ] && [ -n "$PY" ]; then
    ok "对端脚本与解释器就位（$PEER / $PY）"
else
    bad "对端脚本或 python 解释器缺失（PEER=$PEER PY=$PY）"
    echo "RESULT: $pass passed, $fail failed"
    exit 1
fi

# B1: 起对端 → 以 DISPLAY 指向它真实运行被测二进制
# 端口末字节（对端按 6000+末字节 监听），按 PID 分散避免与并发任务撞端口；
# 再现场探测该端口确实无人监听——一次更早的运行被强杀时，对端可能成为「遗留监听」
# （实测本机 :99/TCP 6099 就是这样被占住的），沾上它 bind 会失败，故最多顺延 10 个末字节。
OCTET=$(( ($$ % 200) + 20 ))
_i=0
while [ "$_i" -lt 10 ]; do
    if "$PY" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(1 if s.connect_ex(('127.0.0.1',6000+$OCTET))==0 else 0)" 2>/dev/null; then
        break
    fi
    if [ "$OCTET" -ge 219 ]; then
        OCTET=20
    else
        OCTET=$(( OCTET + 1 ))
    fi
    _i=$(( _i + 1 ))
done
PORT=$(( 6000 + OCTET ))

"$PY" "$PEER" "$OCTET" 60 45 > "$REPORT" 2>&1 &
PEER_PID=$!
# 收到中断信号也要带走对端，避免留下「孤儿监听」毒化后续运行
trap 'kill "$PEER_PID" 2>/dev/null; exit 130' INT TERM HUP
sleep 2

if kill -0 "$PEER_PID" 2>/dev/null; then
    ok "headless X11 对端已在 127.0.0.1:$PORT 监听"
else
    bad "对端未能启动（报告: $(cat "$REPORT" 2>/dev/null | head -3)）"
    echo "RESULT: $pass passed, $fail failed"
    exit 1
fi

# X11 的 DISPLAY=host:N 里 N 是**显示号**，端口 = 6000+N，故这里传末字节 N
DISPLAY=127.0.0.1:$OCTET run_bounded 60 "$BIN" -22
crc=$RUN_RC
cout=$(cat "$RUN_OUT" 2>/dev/null)

# 等对端落完报告（注入错误后自行收尾）
i=0
REP=""
while [ "$i" -lt 45 ]; do
    REP=$(cat "$REPORT" 2>/dev/null)
    case "$REP" in
        *"退出="*)
            break
            ;;
    esac
    if ! kill -0 "$PEER_PID" 2>/dev/null; then
        break
    fi
    sleep 1
    i=$((i + 1))
done
kill "$PEER_PID" 2>/dev/null
REP=$(cat "$REPORT" 2>/dev/null)
rep=$REP

# 对端必须真的收到了连接（setup 握手完成），否则后续断言无意义
case "$rep" in
    *"setup=True"*)
        ok "对端完成 X11 连接握手（setup=True：连接请求应答被客户端接受）"
        ;;
    *)
        bad "对端未完成连接握手（报告: $(echo "$rep" | head -3)）"
        ;;
esac

# B2: 客户端真实拿到显示（未走 \"can't open display\" 失败分支）
case "$cout" in
    *"can't open display"*)
        bad "客户端未能连上对端显示（输出: $cout）"
        ;;
    *)
        ok "客户端 XOpenDisplay 成功（未出现 \"can't open display\"）"
        ;;
esac

# B3: 窗口几何 —— 主窗口与图标窗口均为 64x64 depth 24（源码固定值）
count_match "window 0x"
n_win=$MC
if [ "$n_win" -eq 2 ]; then
    ok "对端记录到 2 个窗口（XCreateSimpleWindow 主窗口 + 图标窗口）"
else
    bad "对端记录到的窗口数应为 2，实测 $n_win"
fi

count_match "64x64 depth=24"
if [ "$MC" -eq 2 ]; then
    # 主窗口与图标窗口均为源码固定几何 64x64/depth=24
    ok "两个窗口几何均为 64x64 depth=24（XCreateSimpleWindow 主窗口 + 图标窗口）"
else
    bad "64x64 depth=24 记录数应为 2，实测 $MC"
fi

count_match "64x64 depth=1"
if [ "$MC" -eq 2 ]; then
    # 一条是 XCreateBitmapFromData 建立，一条是向该位图上传像素
    ok "形状掩码位图为 64x64 depth=1（建立 + 像素上传各 1 条记录）"
else
    bad "64x64 depth=1 记录数应为 2，实测 $MC"
fi

# B4: XPM 位图 —— 134x148 主 pixmap 上传并解码出像素颜色（XpmCreatePixmapFromData）
case "$rep" in
    *"134x148 depth=24"*)
        ok "对端记录到 134x148 depth=24 位图（XPM 主图经 CreatePixmap 建立）"
        ;;
    *)
        bad "未见 134x148 depth=24 位图记录"
        ;;
esac

count_match "134x148 depth=24 fmt=2 颜色数="
if [ "$MC" -eq 0 ]; then
    bad "未见 134x148 depth=24 的 PutImage 解码记录"
else
    _c=${ML##*颜色数=}
    _c=${_c%% *}
    case "$_c" in
        '' | 0)
            bad "XPM 像素未解码出任何颜色（PutImage 内容为空）"
            ;;
        *)
            if [ "$_c" -ge 8 ]; then
                ok "XPM 位图像素解码出 $_c 种颜色（≥8，XpmCreatePixmapFromData 真实上传像素）"
            else
                bad "XPM 像素颜色数仅 $_c（应 ≥8）"
            fi
            ;;
    esac
fi

# B5: 形状遮罩 —— XShapeCombineMask 真实发出（SHAPE 经 QueryExtension 可见）
count_match "SHAPE={'SHAPE': 128}"
if [ "$MC" -ge 1 ]; then
    ok "SHAPE 扩展对客户端可见（major opcode 128）"
else
    bad "对端未正确声明 SHAPE 扩展"
fi

count_match "EXT:SHAPE="
shape_n=${ML##*EXT:SHAPE=}
shape_n=${shape_n%%,*}
case "$shape_n" in
    '' | 0)
        bad "未收到 ShapeMask 请求（形状遮罩未真实执行）"
        ;;
    *)
        ok "收到 ShapeMask 请求 $shape_n 次（XShapeCombineMask 真实执行）"
        ;;
esac

# B6: WM 属性 —— 5 条属性和内容都被服务端记录
prop_ok=0
for p in WM_CLASS WM_COMMAND WM_HINTS WM_NAME WM_NORMAL_HINTS; do
    case "$rep" in
        *"$p"*) prop_ok=$((prop_ok + 1)) ;;
    esac
done
if [ "$prop_ok" -eq 5 ]; then
    ok "5 条 WM 属性全部到达服务端（WM_CLASS/WM_COMMAND/WM_HINTS/WM_NAME/WM_NORMAL_HINTS）"
else
    bad "WM 属性仅到达 $prop_ok/5 条"
fi

case "$rep" in
    *"-22"*)
        ok "WM_COMMAND 内容含命令行参数 \"-22\"（属性内容被真实读取）"
        ;;
    *)
        bad "WM_COMMAND 未记录到参数内容 -22"
        ;;
esac

# B7: 动画主循环 —— 拷贝到窗口的帧数达到注入阈值（即循环真的在画）
count_match "CopyArea 总数="
frames=${ML#*→窗口 }
frames=${frames%% *}
case "$frames" in
    '' | *[!0-9]*)
        bad "未统计到拷贝到窗口的帧数"
        ;;
    *)
        if [ "$frames" -ge 60 ]; then
            ok "拷贝到窗口 $frames 帧（≥60，XCopyArea 动画主循环真实运行）"
        else
            bad "拷贝到窗口仅 $frames 帧（<60）"
        fi
        ;;
esac

# B8: 终止信号 —— 对端注入协议错误并关闭连接，客户端据实报错且非零退出
case "$rep" in
    *"退出=injected_error"*)
        ok "对端按计划注入 BadImplementation 协议错误"
        ;;
    *)
        bad "对端退出原因异常（$(echo "$rep" | grep -a -o '退出=[a-z_]*' | head -1)）"
        ;;
esac

if [ "$crc" -ne 0 ]; then
    ok "客户端在服务端断开后非零退出（rc=$crc）"
else
    bad "客户端退出码应为非零，实测 rc=$crc"
fi

case "$cout" in
    *"X Error"* | *"X connection"*)
        ok "客户端 stderr 报出 X 协议错误/连接中断（对注入错误的真实反应）"
        ;;
    *)
        bad "客户端未报出 X 协议错误（输出: $cout）"
        ;;
esac

if [ -z "$KEEP_WORK" ] && [ "$WORK" != "$HERE" ]; then
    rm -rf "$WORK" 2>/dev/null
fi

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
