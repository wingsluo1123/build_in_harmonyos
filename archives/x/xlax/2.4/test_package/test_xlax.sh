#!/data/service/hnp/bin/bash
# test_package/test_xlax.sh — HarmonyOS PC 消费者测试：装配后二进制与运行时链路
#
# 用法: test_xlax.sh <装配后的 xlax 二进制> <包目录>
#
# xlax 是 X11（Xt + Athena widgets）桌面工具，HarmonyOS PC 没有 X server，
# 因此测试驱动适配后提供的无头路径：
#   * 上游装配事实（二进制、两个手册页、Perl 助手）
#   * --version（适配新增入口，conan smoke 门禁用）
#   * --selftest：12 项程序化检查，真正执行 libXt 并读取 libXaw/libXmu 的数据符号
#   * 无显示错误路径：证明装配后的二进制确实加载并初始化了整条 X11 栈
#   * HarmonyOS ELF 事实：ELF64/AArch64、期望的 DT_NEEDED、且不含 libbsd

set -euo pipefail

BIN="${1:?装配后的 xlax 二进制路径必填}"
PKG="${2:?包目录必填}"

pass=0
fail=0

ok()  { printf '        [ok] %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '        [fail] %s\n' "$1"; fail=$((fail + 1)); }

echo "[step] xlax 消费者测试"
echo "        二进制: $BIN"
echo "        包目录: $PKG"

# ---- 1. 包内容存在性 -----------------------------------------------------
echo "[step] 1/5: 装配内容"

if [ -x "$BIN" ]; then
    ok "bin/xlax 已装配且可执行"
else
    bad "bin/xlax 缺失或不可执行"
fi

if [ -f "$PKG/share/man/man1/xlax.1" ] && grep -q 'xlax' "$PKG/share/man/man1/xlax.1"; then
    ok "share/man/man1/xlax.1 已装配且内容提及 xlax"
else
    bad "share/man/man1/xlax.1 缺失"
fi

if [ -f "$PKG/share/man/man1/mkxlax.1" ]; then
    ok "share/man/man1/mkxlax.1 已装配"
else
    bad "share/man/man1/mkxlax.1 缺失"
fi

if [ -f "$PKG/share/xlax/mkxlax" ] && [ -f "$PKG/share/xlax/dot-mkxlax" ]; then
    ok "Perl 助手 mkxlax 与样例 dot-mkxlax 以数据形式装配在 share/xlax"
else
    bad "share/xlax/mkxlax 或 dot-mkxlax 缺失"
fi

# ---- 2. 版本入口 ---------------------------------------------------------
echo "[step] 2/5: 上游 CLI 合约"

rc=0
out=$("$BIN" --version 2>&1) || rc=$?
first=$(printf '%s\n' "$out" | head -n 1)
if [ "$rc" -eq 0 ] && [ "$first" = "xlax 2.4" ]; then
    ok "--version 输出 'xlax 2.4' 且退出码 0"
else
    bad "--version rc=$rc first line='$first'"
fi

# ---- 3. 鸿蒙无头自检 -----------------------------------------------------
echo "[step] 3/5: --selftest 程序化自检"

rc=0
selftest_out=$("$BIN" --selftest 2>&1) || rc=$?
selftest_ok=$(printf '%s\n' "$selftest_out" | grep -c '^ok  ' || true)
selftest_fail=$(printf '%s\n' "$selftest_out" | grep -c '^FAIL' || true)

if [ "$rc" -eq 0 ] && [ "$selftest_fail" -eq 0 ] && [ "$selftest_ok" -eq 12 ] \
   && printf '%s' "$selftest_out" | grep -q 'selftest: 12/12 checks passed'; then
    ok "xlax --selftest: $selftest_ok 项检查全部通过"
else
    bad "xlax --selftest rc=$rc ok=$selftest_ok fail=$selftest_fail"
    printf '%s\n' "$selftest_out" | sed 's/^/             | /'
fi

if printf '%s\n' "$selftest_out" | grep -q 'libXaw exports the asciiText widget class record'; then
    ok "libXaw 的 widget class 记录在运行期可解析"
else
    bad "libXaw 的 widget class 记录未被 --selftest 覆盖"
fi

# ---- 4. 无显示错误路径 ---------------------------------------------------
echo "[step] 4/5: 无显示错误路径"

rc=0
no_display_out=$(DISPLAY= "$BIN" -find 2>&1) || rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 139 ] && printf '%s' "$no_display_out" | grep -qi 'display'; then
    ok "无显示启动按预期失败闭合，Xt 给出 display 诊断 (rc=$rc)"
else
    bad "无显示启动 rc=$rc out='$no_display_out'"
fi

# ---- 5. HarmonyOS ELF 事实 ----------------------------------------------
echo "[step] 5/5: HarmonyOS ELF 事实"

readelf_tool=""
for candidate in llvm-readelf readelf; do
    if command -v "$candidate" > /dev/null 2>&1; then
        readelf_tool="$candidate"
        break
    fi
done

if [ -n "$readelf_tool" ]; then
    header=$("$readelf_tool" -h "$BIN" 2>/dev/null)
    if printf '%s' "$header" | grep -q 'ELF64' && printf '%s' "$header" | grep -q 'AArch64'; then
        ok "装配后的可执行文件是 ELF64 AArch64"
    else
        bad "装配后的可执行文件不是 ELF64/AArch64"
    fi

    needed=$("$readelf_tool" -d "$BIN" 2>/dev/null | grep NEEDED || true)
    missing=""
    for lib in libXaw.so.7 libXmu.so.6 libXt.so.6 libX11.so.6; do
        printf '%s' "$needed" | grep -q "$lib" || missing="$missing $lib"
    done
    if [ -z "$missing" ]; then
        ok "可执行文件记录 libXaw/libXmu/libXt/libX11 的 DT_NEEDED"
    else
        bad "缺失 DT_NEEDED:$missing"
    fi

    if printf '%s' "$needed" | grep -q 'libbsd'; then
        bad "可执行文件链接了 libbsd（OHOS libc 自带 strlcpy）"
    else
        ok "可执行文件未链接 libbsd"
    fi
else
    echo "        [warn] 无 readelf，跳过 ELF 检查"
fi

# ---- 汇总 ---------------------------------------------------------------
echo "[step] 汇总: $pass passed, $fail failed"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
exit 0
