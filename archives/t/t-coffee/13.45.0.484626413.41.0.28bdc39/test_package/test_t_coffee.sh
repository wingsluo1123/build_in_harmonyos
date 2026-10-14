#!/bin/bash
# test_package/test_t_coffee.sh — t-coffee 13.45.0.484626413.41.0.28bdc39 消费者测试
#
# 全部运行期断言都真实执行本包产出的 bin/t_coffee 并检查其输出；产物取证断言直接
# 读 ELF 字节。无空壳测试、无伪造期望值。
#
# 执行环境三态（与 archives/s/sockstat/0.4.2 同一纪律）：
#   * CI profile 跑在真机 HarmonyOS PC（/data/service/hnp/bin/clang），aarch64 产物
#     原生执行；
#   * x86_64 运行器上若存在 qemu-aarch64，同一产物经 qemu 执行；
#   * 两者都不可用时运行期断言降级为 SKIP，T1 产物取证断言照常执行。
#
# 每次调用都喂 </dev/null：T-Coffee 在读入序列后会交互式地问
# "Identify Master Sequences [no]:"，stdin 若接着管道会读到随机数据。
#
# 每次调用都把 HOME_4_TCOFFEE / DIR_4_TCOFFEE / CACHE_4_TCOFFEE / TMP_4_TCOFFEE
# 指到临时目录：T-Coffee 会在自己的 home 下建 tco/ mcoffee/ methods/ plugins/
# 子目录，默认写 $HOME/.t_coffee，测试不该污染 HOME，也不该写进只读安装目录。
# 调用时的 cwd 也切到临时目录：T-Coffee 会把引导树（*.dnd）、文库（*.lib）等
# 落在当前目录里。
#
# 不用 `set -o pipefail`：脚本里多处 `... | head -N`，head 提前关闭管道会触发
# SIGPIPE(141) 并被 pipefail 误判为失败；管道环节的失败由各断言的显式判据承担。
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export SCRIPT_DIR
EXE="${1:-}"
if [ -z "${EXE}" ] || [ ! -f "${EXE}" ]; then
    echo "FAIL: t_coffee binary not provided or not a file: '${EXE}'"
    exit 1
fi
EXE="$(cd "$(dirname "${EXE}")" && pwd)/$(basename "${EXE}")"
PKG_ROOT="$(cd "$(dirname "${EXE}")/.." && pwd)"

PASS=0; SKIP=0; FAIL=0
TOTAL_ASSERTIONS=29

pass() { echo "OK: $1"; PASS=$((PASS + 1)); }
skip() { echo "SKIP: $1"; SKIP=$((SKIP + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# ── 运行器选择 ────────────────────────────────────────────────────────────
MACHINE="$(uname -m 2>/dev/null || echo unknown)"
case "${MACHINE}" in
    aarch64|arm64) RUNNER=""; RUNNER_DESC="native (${MACHINE})" ;;
    *)
        if command -v qemu-aarch64 >/dev/null 2>&1; then
            RUNNER="qemu-aarch64"
            [ -n "${OHOS_SYSROOT:-}" ] && RUNNER="${RUNNER} -L ${OHOS_SYSROOT}"
            RUNNER_DESC="qemu-aarch64${OHOS_SYSROOT:+ -L \$OHOS_SYSROOT}"
        else
            RUNNER="__none__"
            RUNNER_DESC="unavailable (no native aarch64, no qemu-aarch64)"
        fi
        ;;
esac

WORK="${TMPDIR:-/tmp}/tcoffee_test_$$"
rm -rf "${WORK}"
mkdir -p "${WORK}" || exit 1
trap 'rm -rf "${WORK}"' EXIT
TCOHOME="${WORK}/tcoffee_home"
mkdir -p "${TCOHOME}"
export HOME_4_TCOFFEE="${TCOHOME}"
export DIR_4_TCOFFEE="${TCOHOME}"
export CACHE_4_TCOFFEE="${TCOHOME}"
export TMP_4_TCOFFEE="${TCOHOME}"
export TMPDIR="${WORK}"
# 非交互：上游会问 "Identify Master Sequences [no]:" 之类的问题
export NUMBER_OF_PROCESSORS_4_TCOFFEE=1
# 上游拿 PID 构造锁文件名，硬上限 MAX_N_PID=260000，超了就整轮
# "--ERROR: MAX_N_PID exceded" 后失败退出。本地 WSL 的 pid_max 让 PID 到 33 万
# （实测 Requested: 330563），必挂；CI worker 上 PID 目前只有几万，但那是运气。
# 上游自己给了 MAX_N_PID_4_TCOFFEE 环境变量来抬高，它只影响锁名空间，
# 不参与任何比对计算，所以这里固定抬高以保证跨环境可复现。
export MAX_N_PID_4_TCOFFEE=4194304

echo "[test] binary : ${EXE}"
echo "[test] pkg    : ${PKG_ROOT}"
echo "[test] runner : ${RUNNER_DESC}"
echo "[test] work   : ${WORK}"

# TOOL_RC=199 统一表示"本环境无法执行该产物"
TOOL_RC=0; TOOL_OUT=""
SKIP_EXEC=0
# 每次调用都在临时工作目录里执行：T-Coffee 会在当前目录里落盘（引导树 *.dnd、
# 文库 *.lib、*.html 缓存等），绝不能写进只读的 test_package/ 或安装目录。
run_tcoffee() {
    TOOL_OUT=""; TOOL_RC=199
    [ "${SKIP_EXEC}" -eq 1 ] && return 0
    _rc_attempt=0
    while :; do
        TOOL_OUT="$(cd "${WORK}" && ${RUNNER} "${EXE}" "$@" </dev/null 2>&1)"
        TOOL_RC=$?
        case "${TOOL_OUT}" in
            *"Exec format error"*|*"cannot execute binary file"*)
                SKIP_EXEC=1; TOOL_RC=199; return 0 ;;
        esac
        if [ "${TOOL_RC}" -eq 126 ] || [ "${TOOL_RC}" -eq 127 ]; then
            SKIP_EXEC=1; TOOL_RC=199; return 0
        fi
        # CI worker 进程数耗尽（fork EAGAIN）时会出现两类伪失败：信号死亡
        # （rc>=128，如资源饥饿下的 SIGSEGV）与输出里带 "can't fork"。
        # 对疑似 fork 污染做有界重试；一致性失败（真 SIGSEGV 等）重试后照样
        # FAIL —— 只消除单次 fork 抖动，不放宽任何断言（2026-10-12 构建
        # #85911：19 项 FAIL 里混着 fork: retry，无法判真伪）。
        _fork_dirty=0
        case "${TOOL_RC}" in
            12[89]|1[3-9][0-9]|2[0-5][0-9]) _fork_dirty=1 ;;
        esac
        case "${TOOL_OUT}" in
            *"can't fork"*|*"fork: retry"*|*"Resource temporarily unavailable"*) _fork_dirty=1 ;;
        esac
        if [ "${_fork_dirty}" -eq 1 ] && [ "${_rc_attempt}" -lt 2 ]; then
            _rc_attempt=$((_rc_attempt + 1))
            echo "[retry] 疑似 worker fork 资源不足（rc=${TOOL_RC}），重试 ${_rc_attempt}/2"
            sleep 2
            continue
        fi
        return 0
    done
}

# 字节取证：返回指定偏移起 count 字节的小端十六进制串（不依赖 readelf）。
# dd/od 的 fork 在 worker 进程耗尽时可能失败 → 空输出；空结果隔 1 秒重试一次，
# 真读不出仍为空（T1 各断言语义不变）。
elf_bytes() {
    _hex="$(dd if="$1" bs=1 skip="$2" count="$3" 2>/dev/null | od -An -tx1 | tr -d ' \n')"
    if [ -z "${_hex}" ]; then
        sleep 1
        _hex="$(dd if="$1" bs=1 skip="$2" count="$3" 2>/dev/null | od -An -tx1 | tr -d ' \n')"
    fi
    printf '%s' "${_hex}"
}

# CLUSTAL W 解析：<aln> <name> -> 该行去掉 gap 后的残基串
clustalw_row() {
    awk -v want="$2" '
        NR == 1 { next }
        substr($0, 1, 16) ~ /^ +$/ { next }          # 保守位行
        {
            n = substr($0, 1, 16); sub(/[ \t\r]+$/, "", n)
            if (n != want) next
            s = s substr($0, 17)
        }
        END { gsub(/[ \t\r-]/, "", s); print s }
    ' "$1"
}
# CLUSTAL W 解析：<aln> <name> -> 该行含 gap 的完整串
clustalw_raw() {
    awk -v want="$2" '
        NR == 1 { next }
        substr($0, 1, 16) ~ /^ +$/ { next }
        {
            n = substr($0, 1, 16); sub(/[ \t\r]+$/, "", n)
            if (n != want) next
            s = s substr($0, 17)
        }
        END { gsub(/[ \t\r]/, "", s); print s }
    ' "$1"
}
# CLUSTAL W 解析：<aln> -> 保守位行
clustalw_cons() {
    awk '
        NR == 1 { next }
        substr($0, 1, 16) ~ /^ +$/ { s = s substr($0, 17) }
        END { gsub(/[ \t\r]/, "", s); print s }
    ' "$1"
}
# CLUSTAL W 解析：<aln> -> 出现过的序列名个数
clustalw_names() {
    awk '
        NR == 1 { next }
        substr($0, 1, 16) ~ /^ +$/ { next }
        {
            n = substr($0, 1, 16); sub(/[ \t\r]+$/, "", n)
            if (n != "") seen[n] = 1
        }
        END { print length(seen) }
    ' "$1"
}

# ── T1 产物完整性取证（6 断言）────────────────────────────────────────────
echo "[T1] 产物完整性取证"
if [ -x "${EXE}" ]; then
    pass "bin/t_coffee 存在且可执行"
else
    fail "bin/t_coffee 缺失或不可执行"
fi

MAGIC="$(elf_bytes "${EXE}" 0 4)"
if [ "${MAGIC}" = "7f454c46" ]; then
    pass "ELF magic 正确 (7f454c46)"
else
    fail "ELF magic 错误: '${MAGIC}'"
fi

MACH="$(elf_bytes "${EXE}" 18 2)"
if [ "${MACH}" = "b700" ]; then
    pass "e_machine=183 (AArch64) -- 目标三元组 aarch64-linux-ohos"
else
    fail "e_machine 非 AArch64: '${MACH}' (期望 b700)"
fi

ETYPE="$(elf_bytes "${EXE}" 16 2)"
if [ "${ETYPE}" = "0300" ]; then
    pass "e_type=ET_DYN (PIE 可执行)"
else
    fail "e_type 非 ET_DYN: '${ETYPE}' (期望 0300)"
fi

if [ -s "${PKG_ROOT}/licenses/license.txt" ]; then
    pass "licenses/license.txt 已随包安装（GPL-3.0-or-later）"
else
    fail "licenses/license.txt 缺失或为空"
fi

# 动态加载器：OHOS/HarmonyOS 用的是 musl 的 /lib/ld-musl-aarch64.so.1。
# 实测依据（都是制品仓里由 CI worker 构建发布的包）：
#   puredata/0.54.1 的 bin/pd、bin/pdreceive、bin/pdsend
#   emacs/29.1 的 bin/emacs-29.1
# 全部是 ld-musl-aarch64.so.1；而本地 WSL 交叉工具链 (/opt/lpk-fixed/clang)
# 按 glibc 习惯写成 ld-linux-aarch64.so.1。两个名字都是 aarch64 加载器，
# 与宿主 x86-64 的 ld-linux-x86-64.so.2 都不同 —— 这条断言要拦的是「产物其实
# 是宿主二进制」，所以两个 aarch64 加载器名都接受，但任何一个都找不到就判失败
# （CI 上曾因为只认 ld-linux-aarch64.so.1 而误判，见 2026-10-12 构建 #85480）。
#
# 判据来源（2026-10-14，CI 构建 #86908 修）：
#   上一版判据是「在 4.8 MB 产物上 grep 加载器名字」，要 fork 两次 grep 才能
#   得出否定结论。#86908 两发全空，报出的却是「产物里没有 aarch64 加载器」；
#   同一配方在本机复跑（同一交叉工具链产物，PT_INTERP=/lib/ld-linux-aarch64.so.1）
#   这一条是过的 —— 说明旧判据把「读不到」和「不是 aarch64 产物」混为一谈，
#   否定结论建立在一个 fork 会失败的探针上。
#   现在改为直接解析 ELF 程序头的 PT_INTERP：python3 在这条链路上必然可用
#   （conan 自身就跑在它上面），打印的是**实际解释器路径**而不是布尔命中，
#   并且只用一次进程。grep 仅作为 python 不可用时的兜底保留。
LOADER=""
INTERP="$(python3 "${SCRIPT_DIR}/elf_interp_of.py" "${EXE}" 2>/dev/null || echo ERR:no-python)"
case "${INTERP}" in
    NONE|ERR:*|"")
        if grep -qa "ld-musl-aarch64.so.1" "${EXE}"; then
            LOADER="ld-musl-aarch64.so.1 (grep 兜底)"
        elif grep -qa "ld-linux-aarch64.so.1" "${EXE}"; then
            LOADER="ld-linux-aarch64.so.1 (grep 兜底)"
        fi
        ;;
    *ld-musl-aarch64.so.1*|*ld-linux-aarch64.so.1*)
        LOADER="${INTERP}"
        ;;
    *)
        LOADER=""
        ;;
esac
if [ -n "${LOADER}" ]; then
    pass "解释器为 ${LOADER}（aarch64 动态加载器，非宿主 glibc x86-64）"
else
    fail "产物动态解释器不是 aarch64 加载器：PT_INTERP='${INTERP}'（既非 ld-musl-aarch64.so.1 也非 ld-linux-aarch64.so.1），可能不是 OHOS/aarch64 目标"
fi

# ── T2 版本自证（3 断言）──────────────────────────────────────────────────
echo "[T2] 版本自证（证明跑的是上游 T-COFFEE 本体，不是同名壳）"
run_tcoffee -version
VER_OUT="${TOOL_OUT}"; VER_RC="${TOOL_RC}"
if [ "${VER_RC}" -eq 199 ]; then
    skip "-version 产物不可执行（${RUNNER_DESC}）"
    skip "-version 版本号断言"
    skip "-version BUILD_INFO 断言"
else
    if [ "${VER_RC}" -eq 0 ]; then
        pass "-version 以 rc=0 退出"
    else
        fail "-version rc=${VER_RC}，期望 rc=0"
    fi
    if echo "${VER_OUT}" | grep -q "T-COFFEE Version_13\.45\.0\.4846264"; then
        pass "-version 报出上游版本串 Version_13.45.0.4846264"
    else
        fail "-version 未报出上游版本串: $(echo "${VER_OUT}" | head -1 | cut -c1-110)"
    fi
    if echo "${VER_OUT}" | grep -q "Revision 5becd5d"; then
        pass "-version 带上游 BUILD_INFO（Revision 5becd5d），产物内嵌真实版本信息"
    else
        fail "-version 缺少上游 BUILD_INFO: $(echo "${VER_OUT}" | head -1 | cut -c1-110)"
    fi
fi

# ── T3 真实多序列比对：3 条蛋白（10 断言）─────────────────────────────────
echo "[T3] 真实多序列比对（3 条蛋白序列 -> CLUSTAL W）"
cat > "${WORK}/prot.fasta" <<'EOF'
>seq1
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ
>seq2
MKTAYIAKQRQISFVKSHFSRQDEERLGLIEVQ
>seq3
MQTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ
EOF
ALN="${WORK}/prot.aln"
run_tcoffee "${WORK}/prot.fasta" -output clustalw -outfile "${ALN}"
T3_RC="${TOOL_RC}"
if [ "${T3_RC}" -eq 199 ]; then
    skip "蛋白比对 rc=0"
    skip "CLUSTAL W 头部"
    skip "比对行数=3"
    skip "各行等长"
    skip "seq1 去 gap 还原"
    skip "seq2 去 gap 还原"
    skip "seq3 去 gap 还原"
    skip "保守位含 *"
    skip "* 数与实际全同列数一致"
    skip "比对长度 >= 输入最长序列"
else
    if [ "${T3_RC}" -eq 0 ] && [ -s "${ALN}" ]; then
        pass "蛋白比对 rc=0 且产出非空比对文件"
    else
        fail "蛋白比对 rc=${T3_RC}，比对文件大小 $(wc -c < "${ALN}" 2>/dev/null || echo 0)"
    fi

    HDR="$(head -1 "${ALN}" 2>/dev/null)"
    if [ "${HDR}" = "CLUSTAL W (1.83) multiple sequence alignment" ]; then
        pass "比对文件头为 CLUSTAL W (1.83) multiple sequence alignment"
    else
        fail "比对文件头异常: '${HDR}'"
    fi

    NSEQ="$(clustalw_names "${ALN}")"
    if [ "${NSEQ}" = "3" ]; then
        pass "比对结果含 3 条序列行（输入 3 条）"
    else
        fail "比对结果序列行数=${NSEQ}，期望 3"
    fi

    R1="$(clustalw_raw "${ALN}" seq1)"
    R2="$(clustalw_raw "${ALN}" seq2)"
    R3="$(clustalw_raw "${ALN}" seq3)"
    L1=${#R1}; L2=${#R2}; L3=${#R3}
    if [ "${L1}" -gt 0 ] && [ "${L1}" -eq "${L2}" ] && [ "${L2}" -eq "${L3}" ]; then
        pass "三条比对行等长（${L1} 列），符合多序列比对定义"
    else
        fail "三条比对行长度不等: ${L1}/${L2}/${L3}"
    fi

    S1="$(clustalw_row "${ALN}" seq1)"
    S2="$(clustalw_row "${ALN}" seq2)"
    S3="$(clustalw_row "${ALN}" seq3)"
    I1="$(awk '/^>seq1$/{f=1;next} /^>/{f=0} f' "${WORK}/prot.fasta" | tr -d '\n\r')"
    I2="$(awk '/^>seq2$/{f=1;next} /^>/{f=0} f' "${WORK}/prot.fasta" | tr -d '\n\r')"
    I3="$(awk '/^>seq3$/{f=1;next} /^>/{f=0} f' "${WORK}/prot.fasta" | tr -d '\n\r')"
    if [ "${S1}" = "${I1}" ] && [ -n "${I1}" ]; then
        pass "seq1 行去掉 gap 后与输入序列逐字节一致"
    else
        fail "seq1 行去 gap 还原失败: got='${S1}' want='${I1}'"
    fi
    if [ "${S2}" = "${I2}" ] && [ -n "${I2}" ]; then
        pass "seq2 行去掉 gap 后与输入序列逐字节一致"
    else
        fail "seq2 行去 gap 还原失败: got='${S2}' want='${I2}'"
    fi
    if [ "${S3}" = "${I3}" ] && [ -n "${I3}" ]; then
        pass "seq3 行去掉 gap 后与输入序列逐字节一致"
    else
        fail "seq3 行去 gap 还原失败: got='${S3}' want='${I3}'"
    fi

    CONS="$(clustalw_cons "${ALN}")"
    if echo "${CONS}" | grep -q '\*'; then
        pass "保守位行含 '*'（存在三序列全同列）"
    else
        fail "保守位行没有 '*': '${CONS}'"
    fi

    STARS="$(printf '%s' "${CONS}" | tr -cd '*' | wc -c | tr -d ' ')"
    COLS="$(printf '%s\n%s\n%s' "${R1}" "${R2}" "${R3}" | awk '
        { for (i = 1; i <= length($0); i++) c[NR, i] = substr($0, i, 1) }
        END {
            n = length($1); k = 0
            for (i = 1; i <= n; i++)
                if (c[1, i] != "-" && c[2, i] != "-" && c[3, i] != "-" &&
                    c[1, i] == c[2, i] && c[2, i] == c[3, i]) k++
            print k
        }')"
    if [ "${STARS}" = "${COLS}" ]; then
        pass "保守位 '*' 数（${STARS}）与实际三序列全同列数（${COLS}）一致"
    else
        fail "保守位 '*' 数=${STARS} 与实际全同列数=${COLS} 不一致"
    fi

    MAXIN=0
    for s in "${I1}" "${I2}" "${I3}"; do
        [ ${#s} -gt "${MAXIN}" ] && MAXIN=${#s}
    done
    if [ "${L1}" -ge "${MAXIN}" ]; then
        pass "比对长度 ${L1} >= 输入最长序列 ${MAXIN}（未丢残基）"
    else
        fail "比对长度 ${L1} < 输入最长序列 ${MAXIN}"
    fi
fi

# ── T4 DNA 比对 + fasta 输出往返（6 断言）─────────────────────────────────
echo "[T4] DNA 比对与 fasta 输出往返"
cat > "${WORK}/dna.fasta" <<'EOF'
>dnaA
ATGGCATTAGCTAGCTAGCTTACGATCGATCGGCATCGATCGATTTACGGCAT
>dnaB
ATGGCATTAGCTAGCTAGCTTACGATCGATCGGCATCGATCGATTTACGGC
EOF
DALN="${WORK}/dna.aln"
FALN="${WORK}/dna.fas.out"
run_tcoffee "${WORK}/dna.fasta" -output clustalw -outfile "${DALN}"
T4_RC="${TOOL_RC}"
if [ "${T4_RC}" -eq 199 ]; then
    skip "DNA 比对 rc=0"
    skip "DNA 比对两行等长"
    skip "DNA 比对去 gap 还原"
    skip "-output fasta rc=0"
    skip "fasta 输出记录数=2"
    skip "fasta 去 gap 还原"
else
    if [ "${T4_RC}" -eq 0 ] && [ -s "${DALN}" ]; then
        pass "DNA 比对 rc=0 且产出非空比对文件"
    else
        fail "DNA 比对 rc=${T4_RC}，比对文件大小 $(wc -c < "${DALN}" 2>/dev/null || echo 0)"
    fi

    D1="$(clustalw_raw "${DALN}" dnaA)"
    D2="$(clustalw_raw "${DALN}" dnaB)"
    if [ ${#D1} -gt 0 ] && [ "${#D1}" -eq "${#D2}" ]; then
        pass "DNA 两条比对行等长（${#D1} 列）"
    else
        fail "DNA 两条比对行长度不等: ${#D1}/${#D2}"
    fi

    DI1="$(clustalw_row "${DALN}" dnaA)"
    DI2="$(clustalw_row "${DALN}" dnaB)"
    WANT_D1="$(awk '/^>dnaA$/{f=1;next} /^>/{f=0} f' "${WORK}/dna.fasta" | tr -d ' \t\r\n')"
    WANT_D2="$(awk '/^>dnaB$/{f=1;next} /^>/{f=0} f' "${WORK}/dna.fasta" | tr -d ' \t\r\n')"
    if [ -n "${WANT_D1}" ] && [ "${DI1}" = "${WANT_D1}" ] && [ "${DI2}" = "${WANT_D2}" ]; then
        pass "DNA 两条比对行去掉 gap 后与输入逐字节一致（后者少 1 个碱基的同源序列）"
    else
        fail "DNA 比对去 gap 还原失败: A='${DI1}' B='${DI2}'"
    fi

    run_tcoffee "${WORK}/dna.fasta" -output fasta -outfile "${FALN}"
    T4F_RC="${TOOL_RC}"
    if [ "${T4F_RC}" -eq 0 ] && [ -s "${FALN}" ]; then
        pass "-output fasta rc=0 且产出非空 fasta"
    else
        fail "-output fasta rc=${T4F_RC}，输出大小 $(wc -c < "${FALN}" 2>/dev/null || echo 0)"
    fi

    NREC="$(grep -c '^>' "${FALN}" 2>/dev/null || echo 0)"
    if [ "${NREC}" = "2" ]; then
        pass "fasta 输出含 2 条记录"
    else
        fail "fasta 输出记录数=${NREC}，期望 2"
    fi

    # T-Coffee 的 -output fasta 用 '-' 表示比对缺口（上游行为，x86_64 官方产物
    # 逐字节相同），所以这里去掉换行与 '-' 后与输入比对：既验证了往返无损，
    # 又不会把合法的比对缺口误判成数据损坏。
    FSUM="$(grep -v '^>' "${FALN}" 2>/dev/null | tr -d ' \t\r\n-')"
    if [ -n "${WANT_D1}" ] && [ "${FSUM}" = "${WANT_D1}${WANT_D2}" ]; then
        pass "fasta 输出两条序列去掉换行与 gap 后与输入逐字节一致（往返无损）"
    else
        fail "fasta 输出内容与输入不符: '${FSUM}'"
    fi
fi

# ── T5 鸿蒙特有（4 断言）─────────────────────────────────────────────────
echo "[T5] 鸿蒙特有（交叉编译链接面 / 只读安装目录 / 外架构预编译产物未打包）"
READELF=""
for cand in readelf llvm-readelf llvm-readelf-14 eu-readelf; do
    if command -v "${cand}" >/dev/null 2>&1; then READELF="${cand}"; break; fi
done
if [ -z "${READELF}" ]; then
    skip "动态依赖仅 libc.so（无 readelf 可用，无法取证）"
else
    NEEDED="$(${READELF} -d "${EXE}" 2>/dev/null \
        | sed -n 's/.*NEEDED.*\[\(.*\)\].*/\1/p' | sort | tr '\n' ' ')"
    if [ -z "${NEEDED// /}" ]; then
        fail "readelf -d 未解析出任何 NEEDED 项，无法证明依赖面（输出: ${NEEDED:-<空>}）"
    else
        NONLIBC="$(echo "${NEEDED}" | tr ' ' '\n' | grep -v '^libc\.so$' | grep -v '^$' || true)"
        if [ -z "${NONLIBC}" ]; then
            pass "动态依赖仅 libc.so（NEEDED='${NEEDED}'），libm 已并入 OHOS libc"
        else
            fail "存在非 libc.so 动态依赖: '${NONLIBC}'"
        fi
    fi
fi

LIBFOUND="$(find "${PKG_ROOT}" -name '*.so' -o -name '*.so.*' -o -name '*.a' 2>/dev/null | head -5)"
if [ -z "${LIBFOUND}" ]; then
    pass "包内无 .so/.a（不污染 /lib、/lib64，R26 口径）"
else
    fail "包内出现共享/静态库: $(echo "${LIBFOUND}" | tr '\n' ' ')"
fi

BINS="$(cd "${PKG_ROOT}/bin" 2>/dev/null && ls -1 || true)"
if [ "${BINS}" = "t_coffee" ]; then
    pass "bin/ 只含 t_coffee：上游自带的 x86_64 预编译 bin/linux/t_coffee 未被打包"
else
    fail "bin/ 内容异常（期望只有 t_coffee）: '$(echo "${BINS}" | tr '\n' ' ')'"
fi

# OHOS 上安装目录（/data/service/hnp/...）对应用只读：T-Coffee 必须把自己的
# 缓存/临时目录写到 HOME_4_TCOFFEE 指定的处，而不是往安装目录里写。
PKG_BEFORE="$(find "${PKG_ROOT}" 2>/dev/null | sort)"
if [ "${SKIP_EXEC}" -eq 1 ]; then
    skip "T-Coffee 运行期不在安装目录落盘（产物不可执行）"
else
    run_tcoffee "${WORK}/prot.fasta" -output clustalw -outfile "${WORK}/ro.aln"
    PKG_AFTER="$(find "${PKG_ROOT}" 2>/dev/null | sort)"
    if [ "${PKG_BEFORE}" = "${PKG_AFTER}" ] && [ -d "${TCOHOME}/tco" ]; then
        pass "T-Coffee 把 tco/ 缓存建在 HOME_4_TCOFFEE 下，安装目录零落盘（只读安装安全）"
    elif [ "${PKG_BEFORE}" != "${PKG_AFTER}" ]; then
        fail "T-Coffee 在安装目录 ${PKG_ROOT} 内落了文件（OHOS 只读安装会失败）"
    else
        fail "T-Coffee 未在 ${TCOHOME} 下建立 tco/ 缓存目录，HOME_4_TCOFFEE 约定未生效"
    fi
fi

# ── 汇总 ─────────────────────────────────────────────────────────────────
COUNTED=$((PASS + SKIP + FAIL))
echo "=============================================="
echo "t-coffee 13.45.0.484626413.41.0.28bdc39 消费者测试: ${PASS} passed, ${SKIP} skipped, ${FAIL} failed  (断言计数 ${COUNTED}/${TOTAL_ASSERTIONS})"
if [ "${COUNTED}" -ne "${TOTAL_ASSERTIONS}" ]; then
    echo "FAIL: 断言计数 ${COUNTED} 与声明的 ${TOTAL_ASSERTIONS} 不一致（测试脚本与 MANIFEST.yml 脱节）"
    exit 1
fi
if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
if [ "${PASS}" -eq 0 ]; then
    echo "FAIL: 零 PASS 断言，无有效验证"
    exit 1
fi
exit 0
