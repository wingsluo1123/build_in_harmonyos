#!/bin/sh
# run_test.sh — slcfitsio consumer test driver.
#
# usage: run_test.sh <slcfitsio_package_folder>
#
# R34: this actually executes the installed artifact.  The packaged
# cfitsio-module.so is loaded by the real slsh interpreter out of the
# package tree (SLANG_MODULE_PATH + the S-Lang load path), and the adapted
# upstream regression scripts (test_fits.sl image/binary-table round-trips,
# test_wcs.sl fitswcs bin/rebin) perform real fits/fitswcs round-trips.
#
# Exit status: 0 = all upstream checks passed, non-zero = load failure or at
# least one failed assertion.
#
# ── 覆盖的上游用例 = src/Makefile 的 `test:` 目标 ────────────────────────
# 上游 `test:` 是 `for X in tests/test_*.sl; do slsh $X; done`；本驱动把
# **全部 2 个**脚本逐个执行并逐条给出结论：
#
#   test_fits.sl  图像 + 二进制表写读回环（关键字/注释/日期/BLANK/按行读列）
#   test_wcs.sl   fitswcs 封装层（fitswcs_bin_wcs / fitswcs_rebin_wcs 的
#                 CRPIX / CDELT 断言）
#
# 执行模型（两种都是真的执行，不是 skip）：
#   1) OHOS worker（CI）：profile 的 host/build 同为 ohos-aarch64 ⇒ conan 判定
#      非交叉 ⇒ test() 执行，脚本在 worker 上**原生**跑。实证：CI build #93516
#      的日志里两个脚本各一行 `--- test_fits.sl rc=0` / `--- test_wcs.sl rc=0`，
#      并以 ALL_UPSTREAM_REGRESSIONS_PASSED 结尾（该次跑的是本驱动改动前的
#      版本；改动后同一位置会额外输出 UPSTREAM_CASE / UPSTREAM_SUMMARY 行）。
#   2) 交叉构建机（WSL x86_64）：该机注册了 binfmt_misc + qemu-aarch64，且
#      /opt/ohos-guest 提供 OHOS guest 库；guest 侧 stock musl 缺 OHOS 硬化
#      符号 __fd_chk（libslang.so.2 需要它），故在该 shim 存在时用 LD_PRELOAD
#      注入（仓库既有先例：archives/x/xhk/1.2、archives/m/musicpc/0.35）。真机
#      OHOS libc 自带这些符号、shim 不存在 ⇒ PRELOAD 保持为空，行为不变。
#      交叉 profile 上需 `-c tools.build.cross_building:can_run=true` 才会进入
#      test()（否则 conan 按 can_run=false 跳过并在日志中打印 skip）。
#
# 上游脚本的改写范围只有两处（逐条见 PR 说明与 MANIFEST.yml）：
#   (a) 装载路径前置段指到**已安装的包目录**（上游指构建目录 "."）；
#   (b) 结尾由「只打印 Passed/Failed」改为 exit(0)/exit(1) —— 上游 make test
#       不检查结果、退出码恒为 0，conan 无法感知失败。
# `diff -w` 核对：忽略空白后，两个脚本相对上游原文**只**有上述两处差异，
# 断言逻辑（关键字写读、图像回环、二进制表三列、按行读列、CRPIX/CDELT 比较）
# 逐行相同，没有被删改或放宽；上游原文 sha256 见 MANIFEST.yml。
#
# 输出约定：每个用例一行 `UPSTREAM_CASE PASS|FAIL <file> (rc=N)`，末尾一行
#   `UPSTREAM_SUMMARY <passed>/<total>`，便于 CI 日志直接核对「实测 N」。
# 退出状态：0 = 两个上游用例全部通过；非零 = 装载失败或至少一个用例失败。
# ─────────────────────────────────────────────────────────────────────────
set -eu

PKG="$1"
HERE=$(cd "$(dirname "$0")" && pwd)

[ -d "$PKG" ] || { echo "FAIL: package folder not found: $PKG"; exit 1; }
[ -f "$PKG/lib/slang/v2/modules/cfitsio-module.so" ] || {
    echo "FAIL: cfitsio-module.so missing under $PKG/lib/slang/v2/modules"; exit 1; }
[ -f "$PKG/share/slsh/local-packages/fits.sl" ] || {
    echo "FAIL: the S-Lang wrapper fits.sl is missing"; exit 1; }
[ -f "$PKG/share/slsh/local-packages/fitswcs.sl" ] || {
    echo "FAIL: the S-Lang wrapper fitswcs.sl is missing"; exit 1; }

SLSH=$(command -v slsh 2>/dev/null) || {
    echo "FAIL: slsh not found on PATH (the slang runtime is required)"; exit 1; }

# guest shim（模拟执行模型）：真机不存在则 PRELOAD 为空，等价于原行为
PRELOAD=""
for s in /opt/ohos-guest/lib/libfdchkshim.so /opt/ohos-guest/lib/libarc4shim.so; do
    [ -f "$s" ] && PRELOAD="${PRELOAD:+$PRELOAD:}$s"
done
[ -n "$PRELOAD" ] && echo "guest shims: $PRELOAD"

# A scratch directory next to the script: HMDFS mktemp -d is unreliable
# under a restrictive umask on the device, so avoid $TMPDIR here.
WORK="$HERE/slcfitsio-test-work-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT INT TERM

rc_all=0
upstream_total=0
upstream_pass=0
for t in test_fits test_wcs; do
    upstream_total=$((upstream_total + 1))
    sed "s|@PKG@|$PKG|g" "$HERE/$t.sl" > "$WORK/$t.sl"
    echo "--- slsh $t.sl"
    rc=0
    (
        cd "$WORK"
        SLANG_MODULE_PATH="$PKG/lib/slang/v2/modules${SLANG_MODULE_PATH:+:$SLANG_MODULE_PATH}" \
        LD_PRELOAD="$PRELOAD" \
          "$SLSH" "./$t.sl"
    ) || rc=$?
    echo "--- $t.sl rc=$rc"
    if [ "$rc" -eq 0 ]; then
        upstream_pass=$((upstream_pass + 1))
        echo "UPSTREAM_CASE PASS $t.sl (rc=0)"
    else
        echo "UPSTREAM_CASE FAIL $t.sl (rc=$rc)"
        rc_all=1
    fi
done

echo "UPSTREAM_SUMMARY ${upstream_pass}/${upstream_total}"
[ "$rc_all" -eq 0 ] || { echo "FAIL: at least one upstream regression script failed"; exit 1; }
echo "ALL_UPSTREAM_REGRESSIONS_PASSED"
exit 0
