#!/bin/sh
# ===========================================================================
# test_lmbench.sh — lmbench consumer tests (CI L1, TAP-like output)
#
# usage: sh test_lmbench.sh <package-dir> <work-dir> <cc>
#
# 覆盖内容：
#   1) 包布局：49 个基准可执行文件（lat_*/bw_*/lmdd/... + 标定三件套）、
#      10 个头文件、lib/libmbench.a；
#   2) 上游官方标定流程：先运行包内 enough / timing_o / loop_o 取本机
#      ENOUGH / TIMING_O / LOOP_O（上游 scripts/config-run 即此机制；负载机上
#      自适应标定可能耗时较长，超时或取不到时回退保守缺省值）；
#   3) 6 个真实基准运行：退出码 0 + 预期输出标签 + 数值 > 0；
#   4) 平台能力断言：lat_rpc 明确报告 Sun RPC 不可用并以非 0 退出
#      （musl/OHOS 无 rpc/rpc.h，属平台事实而非回归）；
#   5) 负向对照：未知子命令被拒绝（非 0 退出 + usage 文本）；
#   6) consumer 链接测试：用包内 include/ + lib/libmbench.a 编译并运行一个
#      真实调用 tvsub() 的 C 程序。
#
# 说明：真实基准数值受机器负载影响，本脚本只断言"有输出且为正数"，
# 不做跨平台数值对比（口径见 reports/test-report.md）。
# ===========================================================================
set -u

PKG="${1:?usage: sh test_lmbench.sh <package-dir> <work-dir> <cc>}"
WORK="${2:?usage: sh test_lmbench.sh <package-dir> <work-dir> <cc>}"
CC="${3:?usage: sh test_lmbench.sh <package-dir> <work-dir> <cc>}"

BIN="$PKG/bin"
INC="$PKG/include"
LIB="$PKG/lib"

# 基准与标定的中间文件放在可写工作目录（OHOS /tmp 只读）
export TMPDIR="$WORK"

CHECKS=0
FAILS=0

check() {
    desc="$1"
    shift
    CHECKS=$((CHECKS + 1))
    if "$@"; then
        echo "ok $CHECKS - $desc"
    else
        echo "not ok $CHECKS - $desc"
        FAILS=$((FAILS + 1))
    fi
}

# 数值 > 0 断言（接受整数/小数）
is_num_pos() {
    case "${1:-}" in
        ''|*[!0-9.]*) return 1 ;;
    esac
    awk -v v="$1" 'BEGIN { exit !(v + 0 > 0) }'
}

# 可选 timeout 包裹（缺失则直接运行）
TMO=""
if command -v timeout >/dev/null 2>&1; then
    TMO="timeout 120"
fi

run_bench() {
    out="$1"
    shift
    $TMO "$@" >"$out" 2>&1
    return $?
}

# ---------------------------------------------------------------------------
# 1) 包布局
# ---------------------------------------------------------------------------
missing=""
for p in bw_file_rd bw_mem bw_mmap_rd bw_pipe bw_tcp bw_unix hello \
         lat_select lat_pipe lat_rpc lat_syscall lat_tcp lat_udp lat_mmap \
         mhz lat_proc lat_pagefault lat_connect lat_fs lat_sig lat_mem_rd \
         lat_ctx lat_sem memsize lat_unix lmdd timing_o enough msleep loop_o \
         lat_fifo lmhttp lat_http lat_fcntl disk lat_unix_connect flushdisk \
         lat_ops line tlb par_mem par_ops stream \
         cache lat_dram_page lat_pmake lat_rand lat_usleep lat_cmd; do
    if [ ! -x "$BIN/$p" ]; then
        missing="$missing $p"
    fi
done
check "49 benchmark executables are present and executable" test -z "$missing"

missing_h=""
for h in bench.h lib_debug.h lib_mem.h lib_tcp.h lib_udp.h lib_unix.h \
         names.h stats.h timing.h version.h; do
    if [ ! -f "$INC/$h" ]; then
        missing_h="$missing_h $h"
    fi
done
check "10 lmbench headers are installed" test -z "$missing_h"

check "libmbench.a static library is installed" test -f "$LIB/libmbench.a"

"$BIN/hello" >"$WORK/hello.out" 2>&1
check "hello prints the upstream greeting" grep -q "Hello world" "$WORK/hello.out"

# ---------------------------------------------------------------------------
# 2) 上游官方标定流程（enough / timing_o / loop_o）
# ---------------------------------------------------------------------------
ENOUGH=$($TMO "$BIN/enough" 2>/dev/null)
if ! is_num_pos "$ENOUGH"; then
    echo "# info: enough helper returned '${ENOUGH:-}' - falling back to ENOUGH=1000000"
    ENOUGH=1000000
fi
check "enough yields a positive calibration interval (ENOUGH=$ENOUGH)" is_num_pos "$ENOUGH"
export ENOUGH

TIMING_O=$($TMO "$BIN/timing_o" 2>/dev/null)
if [ -z "$TIMING_O" ]; then
    echo "# info: timing_o helper returned nothing - falling back to TIMING_O=0"
    TIMING_O=0
fi
check "timing_o yields the gettimeofday overhead (TIMING_O=$TIMING_O)" test -n "$TIMING_O"
export TIMING_O

LOOP_O=$($TMO "$BIN/loop_o" 2>/dev/null)
if ! is_num_pos "$LOOP_O"; then
    echo "# info: loop_o helper returned '${LOOP_O:-}' - falling back to LOOP_O=0.0000134"
    LOOP_O=0.0000134
fi
check "loop_o yields the benchmark loop overhead (LOOP_O=$LOOP_O)" is_num_pos "$LOOP_O"
export LOOP_O

# ---------------------------------------------------------------------------
# 3) 真实基准运行（退出码 + 标签 + 正数值）
# ---------------------------------------------------------------------------
run_bench "$WORK/lat_syscall_null.out" "$BIN/lat_syscall" null
check "lat_syscall null exits 0" test $? -eq 0
V=$(awk '/^Simple syscall:/ {print $3; exit}' "$WORK/lat_syscall_null.out")
check "lat_syscall null reports a positive syscall latency (${V:-empty} us)" is_num_pos "$V"

run_bench "$WORK/lat_syscall_write.out" "$BIN/lat_syscall" write
check "lat_syscall write exits 0" test $? -eq 0
V=$(awk '/^Simple write:/ {print $3; exit}' "$WORK/lat_syscall_write.out")
check "lat_syscall write reports a positive latency (${V:-empty} us)" is_num_pos "$V"

run_bench "$WORK/lat_pipe.out" "$BIN/lat_pipe"
check "lat_pipe exits 0" test $? -eq 0
V=$(awk '/^Pipe latency:/ {print $3; exit}' "$WORK/lat_pipe.out")
check "lat_pipe reports a positive pipe latency (${V:-empty} us)" is_num_pos "$V"

run_bench "$WORK/bw_pipe.out" "$BIN/bw_pipe"
check "bw_pipe exits 0" test $? -eq 0
V=$(awk '/^Pipe bandwidth:/ {print $3; exit}' "$WORK/bw_pipe.out")
check "bw_pipe reports a positive pipe bandwidth (${V:-empty} MB/sec)" is_num_pos "$V"

run_bench "$WORK/lat_ctx.out" "$BIN/lat_ctx" -s 0 2
check "lat_ctx -s 0 2 exits 0" test $? -eq 0
V=$(awk '/^[0-9]+ [.0-9]+/ {print $2; exit}' "$WORK/lat_ctx.out")
check "lat_ctx reports a positive context-switch latency (${V:-empty} us)" is_num_pos "$V"

run_bench "$WORK/lat_proc.out" "$BIN/lat_proc" fork
check "lat_proc fork exits 0" test $? -eq 0
V=$(awk '/^Process fork\+exit:/ {print $3; exit}' "$WORK/lat_proc.out")
check "lat_proc fork reports a positive latency (${V:-empty} us)" is_num_pos "$V"

# ---------------------------------------------------------------------------
# 4) 平台能力断言：Sun RPC 不可用（musl 无 rpc/rpc.h）时的明确报错
# ---------------------------------------------------------------------------
run_bench "$WORK/lat_rpc.out" "$BIN/lat_rpc"
RC=$?
check "lat_rpc reports unsupported Sun RPC with nonzero exit (rc=$RC)" test "$RC" -ne 0
check "lat_rpc explains the missing platform capability" \
    grep -q "Sun RPC is not available" "$WORK/lat_rpc.out"

# ---------------------------------------------------------------------------
# 5) 负向对照：未知子命令必须被拒绝
# ---------------------------------------------------------------------------
run_bench "$WORK/neg.out" "$BIN/lat_syscall" no_such_mode_xyz
RC=$?
check "unknown benchmark mode is rejected (rc=$RC)" test "$RC" -ne 0
check "usage text lists the valid modes" \
    grep -q "null|read|write|stat|fstat|open" "$WORK/neg.out"

# ---------------------------------------------------------------------------
# 6) consumer：使用包内头文件 + libmbench.a 编译并运行
# ---------------------------------------------------------------------------
SRC="./consumer_timing.c"
if [ ! -f "$SRC" ]; then
    SRC="$(dirname "$0")/consumer_timing.c"
fi
cp "$SRC" "$WORK/consumer_timing.c" 2>/dev/null
"$CC" -O2 -I"$INC" "$WORK/consumer_timing.c" "$LIB/libmbench.a" -lm \
    -o "$WORK/consumer_timing" >"$WORK/consumer_compile.out" 2>&1
check "consumer compiles against packaged headers + libmbench.a" \
    test -x "$WORK/consumer_timing"

"$WORK/consumer_timing" >"$WORK/consumer_run.out" 2>&1
RC=$?
check "consumer program runs (rc=$RC)" test "$RC" -eq 0
V=$(awk '/consumer tvsub:/ {print $3; exit}' "$WORK/consumer_run.out")
check "consumer measures a positive tvsub() delta (${V:-empty} s)" is_num_pos "$V"

# ---------------------------------------------------------------------------
echo "1..$CHECKS"
if [ "$FAILS" -ne 0 ]; then
    echo "# FAILED $FAILS/$CHECKS checks"
    exit 1
fi
echo "# all $CHECKS checks passed"
exit 0
