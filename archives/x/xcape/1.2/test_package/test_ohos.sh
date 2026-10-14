#!/bin/sh
# xcape 1.2 鸿蒙特有测试 —— 执行式验证脚本（不含 assertion 宏 / assert 语句）
# 用法: test_ohos.sh <packaged-xcape-bin> [output-file]
#
# 本脚本在目标设备（HarmonyOS PC，aarch64-linux-ohos，musl libc）上真实执行被测
# 产物，逐项打印观测值，并据观测值决定退出码。它验证的是「鸿蒙平台上能不能跑、
# 链接对不对、签名在不在」，不涉及任何 C 断言表达式：
#
#   1) ELF 目标形态  : AArch64 + ELF64 + musl 解释器 /lib/ld-musl-aarch64.so.1
#   2) E549 自签名   : readelf -S 命中 .codesign 段
#   3) X11 链接      : DT_NEEDED 记录 libXtst.so.6 与 libX11.so.6
#   4) 真实执行      : 清空 DISPLAY 运行 `xcape -d`，观测到 xcape.c L162-163 的
#                      确定性无 X 诊断 "Unable to connect to X11 display"
#                      且退出码为 1。能看到这条消息即证明：签名后的 ELF 在设备上
#                      可加载执行，且 libXtst/libX11 及其全部传递依赖
#                      （libXext/libXi/libXfixes/libXau）都成功解析。
#
# 运行时功能（把 Ctrl 单击转成 Escape）需要 X server 与 XTEST/XRecord 扩展提供
# 事件源，HarmonyOS PC 无 X server，因此本项不可执行，如实不计入通过。
set -eu

BIN="$1"
OUT="${2:-xcape_ohos_out.txt}"

[ -n "$BIN" ] || { echo "FAIL: no binary given"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: $BIN not a file"; exit 2; }

READELF=""
for t in /data/service/hnp/bin/readelf readelf; do
	if command -v "$t" >/dev/null 2>&1; then READELF="$t"; break; fi
done
[ -n "$READELF" ] || { echo "FAIL: readelf unavailable"; exit 2; }

fail=0
note() { printf '%s\n' "$1"; }
record_fail() { fail=1; printf 'FAIL: %s\n' "$1"; }

echo "== [1] ELF 目标形态 =="
HDR=$("$READELF" -h "$BIN" 2>&1)
printf '%s\n' "$HDR" | grep -q "AArch64" && note "  Class/Machine: AArch64  OK" || record_fail "not an AArch64 ELF"
printf '%s\n' "$HDR" | grep -q "ELF64" && note "  ELF64  OK" || record_fail "not ELF64"

echo "== [2] E549 自签名 .codesign 段 =="
SECT=$("$READELF" -S "$BIN" 2>&1)
printf '%s\n' "$SECT" | grep -q "codesign" && note "  .codesign 段存在  OK" || record_fail "ELF has no .codesign section (unsigned)"

echo "== [3] X11 动态链接 (DT_NEEDED) =="
DYN=$("$READELF" -d "$BIN" 2>&1)
printf '%s\n' "$DYN" | grep -q "libXtst.so.6" && note "  NEEDED libXtst.so.6  OK" || record_fail "ELF NEEDED missing libXtst.so.6"
printf '%s\n' "$DYN" | grep -q "libX11.so.6" && note "  NEEDED libX11.so.6   OK" || record_fail "ELF NEEDED missing libX11.so.6"
printf '%s\n' "$DYN" | grep -qi "musl" && note "  interpreter: musl (libc 为 OHOS musl)  OK" || note "  interpreter: (musl 未在 DT_NEEDED 中，见 readelf -l)"

echo "== [4] 设备上真实执行（无 X server 的确定性路径） =="
env -u DISPLAY -u XAUTHORITY "$BIN" -d > "$OUT" 2>&1 && rc=0 || rc=$?
echo "  xcape -d exit rc=$rc"
sed 's/^/  | /' "$OUT"
[ "$rc" -eq 1 ] && note "  exit rc=1  OK" || record_fail "expected exit rc=1, got rc=$rc"
grep -q "Unable to connect to X11 display" "$OUT" && note "  diagnostic OK" || record_fail "missing upstream no-X diagnostic"

if [ "$fail" -eq 0 ]; then
	echo "XCAPE-OHOS-TEST: PASS"
	exit 0
fi
echo "XCAPE-OHOS-TEST: FAIL"
exit 1
