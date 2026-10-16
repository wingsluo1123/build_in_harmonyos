#!/data/service/hnp/bin/bash
# Consumer verification for procdump/2.2.
#
# usage: test.sh [--execute | --static-only]
#   --execute      also run the installed binary (host can exec aarch64/OHOS)
#   --static-only  skip the runtime layer (cross build on an x86_64 host)
#
# Static layer (6 assertions)
#   1  bin/procdump exists, is a regular file and is executable
#   2  bin/procdump is an ELF (sanity: the recipe packaged the built artifact)
#   3  share/man/man1/procdump.1 is installed
#   4  the man page describes procdump
#   5  the executable embeds the CLR profiler: a second ELF64/little-endian/
#      AArch64/ET_DYN header is present in its bytes (the profiler .so is linked
#      in as raw data by the recipe's generated embed_profiler.S)
#   6  the executable carries no glibc FORTIFY (__*_chk) references -- musl's libc
#      exports none of them, so such a binary links but dies at load time with
#      "Error relocating ...: __vsnprintf_chk: symbol not found"
#
# Runtime layer (5 assertions, --execute only)
#   7  `procdump -?` prints the "Capture Usage" block
#   8  `procdump -?` prints the "Options" block
#   9  `procdump -?` lists the -pgid switch
#  10  `procdump -?` lists the -sig switch
#  11  the exit code matches what upstream's main() actually does for a usage
#      request, and is NOT 127 ("Error relocating ...: symbol not found") nor a
#      crash (128+signal). Upstream Procdump.c main() originally was:
#          PrintBanner(); InitProcDump();
#          if (geteuid() != 0) { Log(warn, ...); PrintUsage(); }
#          else { if (GetOptions(...) != 0) exit(-1); ... MonitorProcesses(...); }
#      With patch 0004 (ohos-nonroot-run, see conandata.yml) the root gate is
#      dropped: GetOptions() runs at any euid, so `-?` always takes the usage
#      branch -> prints usage -> exit(-1) = 255. EXPECT_RC below is therefore a
#      constant 255 for both root and non-root workers.
#
# WHY EVERY ASSERTION PRINTS A RESULT (2026-10-12):
#   This script used to rely on `set -e` + bare `grep -q` chains.  CI builds
#   #83996 / #84412 / #84441 / #85201 / #85476 / #85645 all died with
#   "ConanException: Error 1" and NOT ONE LINE saying which check failed: the
#   first failing `grep -q` exits the shell with no message, and the captured
#   `-?` output is never shown because `head -5` only ever prints the banner.
#   Six builds were spent unable to tell "usage block missing" from "wrong exit
#   code" from "worker cannot run the binary at all".  Now every check reports
#   [ok]/[FAIL] explicitly and a failure dumps the whole captured output.
#
# Assertions 5 and 6 read the artifact through `od` into a hex view and grep that
# TEXT, never `grep -a` the raw binary.  See the note next to assertion 5.

set -u

MODE="${1:---execute}"

FAILED=0
ok()  { echo "  [ok]   $*"; }

# ── fork 能力自检（2026-10-14，MR 15275）───────────────────────────────────
# 同一提交在部分 worker 上会被 EAGAIN 打死：日志里出现十几行
#   test.sh: fork: (retry: )Resource temporarily unavailable
# 然后 conan 只报 "Error 254"，没有一条 [FAIL] —— 那既不是产物问题也不是断言失败，
# 而是该 worker 的进程数已耗尽（对照：同样的提交在 CI-008/CI-011 上 fork=0 且全绿）。
# 这里先探一次并打印结论，让 CI 日志能自证原因，避免下一次又被误读成代码缺陷。
_fork_probe() {
    local i
    for i in 1 2 3 4 5; do
        if ( : ) 2>/dev/null; then return 0; fi
        sleep 2
    done
    return 1
}
if _fork_probe; then
    echo "env: fork OK（本机可派生进程）"
else
    echo "env: ⚠ fork 受限 —— 本机进程数已耗尽（连续 5 次 EAGAIN）"
    echo "env:   test.sh 的断言会以 'fork: Resource temporarily unavailable' 被打断，"
    echo "env:   conan 侧只会显示 Error 254/1 而没有 [FAIL] 行；这不是产物缺陷，请在空闲 worker 上重跑。"
fi
bad() { echo "  [FAIL] $*" >&2; FAILED=1; }
# chk_pat <label> <pattern> <file>  —— 用 -e 传 pattern，兼容以 '-' 开头的开关名
chk_pat() {
    if grep -q -e "$2" -- "$3"; then ok "$1  (pattern: $2)"; else bad "$1  (pattern: $2 未命中)"; fi
}

# 2026-10-14（MR 15275）：产物路径的推导**不能依赖 fork**。
#   worker 在进程数耗尽时，`$(dirname ...)`（外部命令）会替换为空，路径随即塌成
#   `/share/man/man1/procdump.1`，于是「man page 其实在包里」被误报成「缺失」——
#   CI 日志里 `bin: .../procdump ( bytes)` 的空大小与紧随其后的
#   `grep: /share/man/man1/procdump.1: No such file or directory` 就是同一原因。
#   这里改用 bash 参数展开取包根，只依赖内置命令：
#     BIN=/pkg/bin/procdump  →  PKG_ROOT=/pkg
BIN="$(command -v procdump || true)"
PKG_ROOT="${BIN%/bin/procdump}"
if [ "$PKG_ROOT" = "$BIN" ] || [ -z "$PKG_ROOT" ]; then
    # 没命中预期布局时保留原路径参与断言，并说明清楚，绝不静默指向根目录
    PKG_ROOT=""
    echo "note: procdump 不在 <pkg>/bin/procdump 布局下（command -v 得到 '$BIN'），后续路径断言将按此判定"
fi
MAN="$PKG_ROOT/share/man/man1/procdump.1"

echo "== static layer (mode=$MODE)"
if [ -n "$BIN" ] && [ -f "$BIN" ] && [ -x "$BIN" ]; then
    ok "[1] bin/procdump exists, is a regular file and is executable"
else
    bad "[1] bin/procdump 不可用（command -v 得到 '$BIN'，既不存在也不可执行）—— 后续断言无法进行"
    echo "PASS/FAIL: static verification aborted at assertion [1]" >&2
    exit 1
fi
_size="$(wc -c < "$BIN" 2>/dev/null || true)"
if [ -n "$_size" ]; then echo "bin: $BIN ($_size bytes)"; else echo "bin: $BIN (大小取不到：fork 受限)"; fi

if head -c 4 "$BIN" | grep -q ELF; then ok "[2] bin/procdump is an ELF"; else bad "[2] bin/procdump 不是 ELF"; fi

if [ -n "$MAN" ] && [ -f "$MAN" ] && [ -s "$MAN" ]; then
    ok "[3] man page installed and non-empty ($MAN)"
    if grep -qi "procdump" "$MAN"; then ok "[4] man page describes procdump"; else bad "[4] man page 未提到 procdump"; fi
else
    # 文件不存在/为空时只报 [3]，不要再用 grep 去撞一次必然失败的外部命令
    bad "[3] man page 缺失或为空（$MAN）"
    bad "[4] man page 未提到 procdump（[3] 失败时跳过内容检查）"
fi

# The recipe embeds ProcDumpProfiler.so into the executable as raw bytes with a
# generated embed_profiler.S (the `_binary_obj_ProcDumpProfiler_so_{start,end}`
# pair GNU `ld -r -b binary` would produce).  Prove the embed really happened by
# the blob's own ELF header: 7f 45 4c 46 | 02 01 01 00 | 00 x 8 | 03 00 b7 00
# is ELF64, little endian, e_type=ET_DYN, e_machine=EM_AARCH64(183).
#
# The executable's own first 20 bytes are exactly that pattern too (it is a
# position-independent AArch64 executable), so they are skipped with `od -j 20`;
# anything left is an embedded object, and the only one this build links in is
# the profiler.
#
# Why not `grep -qa "CorProfiler::CleanupProfiler: Enter" "$BIN"` as before?  That
# was the only assertion in the whole repo that gated on a raw `grep -a` scan of
# a multi-megabyte aarch64 binary, and on the OHOS worker it reports "no match"
# for a literal that is demonstrably inside the file: CI build #79451 shipped a
# 5,523,968-byte procdump, which is exactly the 5,291,616-byte ProcDumpProfiler.so
# the OHOS NDK clang 15.0.4 produces from these sources, plus 232,352 bytes of
# the tool's own objects -- and the literal sits at offset 375,469 of that .so.
# Every other ELF-content check in this repo reads readelf's *text* output and
# greps that instead (spinner F1-F7, oomd [8]); spinner's `grep -a -c` survives
# only because it counts must-be-zero hits, which a non-scanning grep passes
# vacuously.
# The hex views go through files rather than `od | tr | grep -q`: `grep -q` exits
# at the first match, and under `set -o pipefail` that would SIGPIPE the writers
# and turn a PASS into a FAIL on whichever grep happens to stream.
ELF_HDR='7f454c460201010000000000000000000300b700'
HEX_TAIL="$(mktemp 2>/dev/null || echo ./procdump_hex_tail.$$)"
od -An -v -tx1 -j 20 "$BIN" | tr -d ' \n' > "$HEX_TAIL"
chk_pat "[5] embedded CLR profiler blob" "$ELF_HDR" "$HEX_TAIL"
rm -f "$HEX_TAIL"

# FORTIFY regression guard. musl has no __*_chk entry points; upstream's
# -D_FORTIFY_SOURCE=2 therefore yields a binary that links and then fails to load.
# Matched by exact name, never by a wildcard: -fstack-protector-all is kept and
# legitimately imports __stack_chk_guard / __stack_chk_fail.
HEX_VIEW="$(mktemp 2>/dev/null || echo ./procdump_hex.$$)"
od -An -v -tx1 "$BIN" | tr -d ' \n' > "$HEX_VIEW"
for s in __vsnprintf_chk __strcpy_chk __strlen_chk __send_chk __recv_chk __write_chk; do
    h="$(printf '%s' "$s" | od -An -v -tx1 | tr -d ' \n')"
    if grep -q "$h" "$HEX_VIEW"; then
        bad "[6] glibc FORTIFY symbol referenced ($s); musl libc cannot resolve it"
    fi
done
[ "$FAILED" -eq 0 ] && ok "[6] no glibc FORTIFY references"
rm -f "$HEX_VIEW"

if [ "$MODE" = "--static-only" ]; then
    if [ "$FAILED" -eq 0 ]; then
        echo "PASS: procdump consumer static verification (6 assertions); runtime layer deferred"
        exit 0
    fi
    echo "FAIL: procdump consumer static verification（见上面的 [FAIL] 行）" >&2
    exit 1
fi

echo
echo "== runtime layer"
EUID_NOW="$(id -u 2>/dev/null || echo '?')"
OUT_FILE="$(mktemp 2>/dev/null || echo ./procdump_help_tmp.txt)"
# ProcDump 2.2 has no -h: GetOptions() only treats -? / /? (and a bad argument
# count) as a usage request, so "-h" is parsed as a Process_Name and the tool
# exits after "No process matching the specified name (-h) can be found" --
# without ever printing the usage block.
# 平台信息（OHOS worker 与本地 Linux 的 uname 行为不同 —— 见 T374：OHOS 上 uname -s 报 HarmonyOS）。
# procdump 的 CheckKernelVersion() 按 uname().release 判「内核 >= 3.5」，CI #85837 里正是它
# 在打印用法块**之前**就 exit(-1)（只能看到 banner）。把 uname 原样记进日志，下次不用再猜。
echo "platform: uname -a => $(uname -a 2>&1 | head -1)"
if [ -r /proc/version ]; then echo "platform: /proc/version => $(head -c 160 /proc/version 2>&1)"; fi
"$BIN" -? > "$OUT_FILE" 2>&1
RC=$?
echo "run: euid=$EUID_NOW rc=$RC bytes=$(wc -c < "$OUT_FILE") lines=$(wc -l < "$OUT_FILE")"
head -5 "$OUT_FILE"

chk_pat "[7] prints the Capture Usage block"  "Capture Usage" "$OUT_FILE"
chk_pat "[8] prints the Options block"        "Options:"      "$OUT_FILE"
chk_pat "[9] lists the -pgid switch"          "-pgid"         "$OUT_FILE"
chk_pat "[10] lists the -sig switch"          "-sig"          "$OUT_FILE"

# [11] 0004 patch（ohos-nonroot-run）后 main() 不再按 euid 分叉：`-?` 一律走
# GetOptions() 的 usage 请求分支 → 打印 usage 并 exit(-1)=255（root 与非 root 一致，
# 见文件头注释与 patches/0004）。EXPECT_RC 因此恒定 255；127 仍是 relocation 失败，
# >=128 且 !=255 才判为信号崩溃。
EXPECT_RC=255
if [ "$RC" -eq "$EXPECT_RC" ]; then
    ok "[11] exit code $RC == $EXPECT_RC（0004 patch 后 -? 走 GetOptions usage 分支）"
elif [ "$RC" -eq 127 ]; then
    bad "[11] exit code 127 —— 动态链接/relocation 失败（缺符号），不是正常用法退出"
elif [ "$RC" -ge 128 ]; then
    # 退出码本身分不出「128+信号=崩溃」与「程序自己 exit(-1)=255」：shell 两者都报 255 级别。
    # 别再把 255 直接断言成「被信号打死」（本文件上一版就这么写过，CI worker 上 euid≠0 时误导排查）。
    bad "[11] exit code $RC（>=128：可能是 128+signal 崩溃，也可能是程序自己 exit(-1)=255）；期望 $EXPECT_RC"
else
    bad "[11] exit code $RC != $EXPECT_RC"
fi

if [ "$FAILED" -ne 0 ]; then
    echo "--- '$BIN -?' 的完整输出（euid=$EUID_NOW rc=$RC）---" >&2
    cat "$OUT_FILE" >&2
    echo "--- 输出结束 ---" >&2
    rm -f "$OUT_FILE"
    echo "FAIL: procdump consumer verification（见上面的 [FAIL] 行）" >&2
    exit 1
fi
rm -f "$OUT_FILE"

echo
echo "PASS: procdump consumer verification (6 static + 5 runtime assertions)"
