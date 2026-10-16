#!/data/service/hnp/bin/bash
# OHOS 适配版 runProcDumpAndValidate（procdump 2.2 上游测试真实执行层的一部分）。
#
# 场景脚本（tests/integration/scenarios/*.sh，上游 2.2 逐字原样）source 本文件后
# 调用 runProcDumpAndValidate，语义与上游同名脚本一致：
#   1) 启动一个真实负载进程（等价于上游 stress-ng 负载）
#   2) 后台启动打包的 procdump，按场景参数（-c/-cl/-m/-ml/-fc/-tc/复合/无触发）监视
#   3) 等待 30 秒监视窗口，结束两者
#   4) 校验转储目录是否按 shouldDump 产生/不产生转储文件，输出 PASS/FAIL
#
# 与上游的两点环境适配（场景脚本零改动；上游原版见 runProcDumpAndValidate.upstream.sh
# 供审计对照）：
#   * stress-ng 负载 → OHOS 可用的等价负载：
#       - CPU 负载：stressPercentage>=60 → ProcDumpTestApplication burn（~100% CPU），
#         <60 → sleep（~0%）。与场景触发/不触发边界一致：high_cpu -c 80（burn 100>80
#         触发）、high_cpu_notdump 20<80（sleep 0<80 不触发）、low_cpu -cl 20（sleep
#         0<20 触发）、low_cpu_notdump 80>20（burn 100>20 不触发）。
#       - MEM 负载：stressPercentage=NNM → memload NN（malloc+memset 精确 RSS=NN MB），
#         匹配 -m/-ml 阈值边界（high_mem -m 80：90M 触发；high_mem_notdump 60M 不触发；
#         low_mem -ml 80：40M 触发；low_mem_notdump 200M 不触发）。
#       - fd/tc 负载：ProcDumpTestApplication 的 fc（500 fd）/tc（100 线程）原生支持。
#   * procdump 与负载生成器路径：PROCDUMP_BIN（打包产物绝对路径）由执行入口
#     run_upstream_ohos.sh 导出；负载生成器位于本脚本同目录的 bin/ 下。
#   * mktemp 用 toybox 兼容语法（无 -t）；转储目录校验用 ls -A（toybox find 无
#     -mindepth 的等价性不可靠）。
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function runProcDumpAndValidate {
    PROCDUMPPATH="${PROCDUMP_BIN:?PROCDUMP_BIN must be exported by run_upstream_ohos.sh}"

    # Make absolutely sure we cleanup dumps from prior run
    DUMP_BASE="${TMPDIR:-/data/local/tmp}"
    rm -rf "$DUMP_BASE"/dump_* 2>/dev/null

    dumpDir=$(mktemp -d "$DUMP_BASE/dump_XXXXXX" 2>/dev/null)
    if [ -z "$dumpDir" ] || [ ! -d "$dumpDir" ]; then
        echo "[ohos-load] FATAL: mktemp -d $DUMP_BASE/dump_XXXXXX failed (TMPDIR=$TMPDIR)"
        return 1
    fi
    cd "$dumpDir" || return 1

    dumpParam=""
    if [ "$#" -ge "6" ] && [ -n "$6" ]; then
        dumpParam="$dumpDir/$6"
    fi

    pid=""
    pidPD=""
    if [ -n "${TESTPROGNAME:-}" ]; then
        # by_name 系列：被监视进程 = ProcDumpTestApplication（上游 Makefile 亦编译同名 bin）
        TESTPROGPATH="$HERE/bin/$TESTPROGNAME"
        echo "[ohos-load] $TESTPROGPATH $TESTPROGMODE &"
        ( "$TESTPROGPATH" "$TESTPROGMODE" ) &
        pid=$!
        # Give test app opportunity to start and get into scenario state
        sleep 5
        echo "[ohos-procdump] $PROCDUMPPATH -log $2 $3 $dumpParam $TESTPROGNAME"
        "$PROCDUMPPATH" -log $2 $3 "$dumpParam" "$TESTPROGNAME" &
        pidPD=$!
    else
        # stress-ng 等价负载（见文件头注释）
        case "$1" in
            *[Mm])
                mb="${1%[Mm]}"
                echo "[ohos-load] memload $mb MB &"
                "$HERE/bin/memload" "$mb" &
                ;;
            *)
                if [ "$1" -ge 60 ]; then mode=burn; else mode=sleep; fi
                echo "[ohos-load] ProcDumpTestApplication $mode &"
                "$HERE/bin/ProcDumpTestApplication" "$mode" &
                ;;
        esac
        pid=$!
        sleep 5
        echo "[ohos-procdump] $PROCDUMPPATH -log $2 $3 $pid $dumpParam"
        "$PROCDUMPPATH" -log $2 $3 "$pid" "$dumpParam" &
        pidPD=$!
    fi

    # 30s monitoring window (upstream semantics)
    sleep 30
    if [ -n "$pidPD" ]; then kill "$pidPD" 2>/dev/null; fi
    if [ -n "$pid" ]; then kill "$pid" 2>/dev/null; fi

    if [ -n "$(ls -A "$dumpDir" 2>/dev/null)" ]; then
        if $4; then
            echo "[ohos-validate] dump produced, shouldDump=true -> PASS"
            return 0
        else
            echo "[ohos-validate] dump produced but shouldDump=false -> FAIL"
            return 1
        fi
    else
        if $4; then
            echo "[ohos-validate] no dump but shouldDump=true -> FAIL"
            return 1
        else
            echo "[ohos-validate] no dump, shouldDump=false -> PASS"
            return 0
        fi
    fi
}
