#!/bin/sh
# test_wob_ohos.sh — wob OHOS aarch64 专属消费者验证（本 run 新增，非上游用例）
#
# 覆盖 OHOS 适配点（配方配置引入的平台差异）：
#   A1) 目标 ABI：bin/wob 必须是 AArch64 ELF（profile arch=armv8 → aarch64）
#   A2) musl 差异：ELF interpreter 必须是 ld-musl-aarch64（OHOS PC 为
#       musl libc，非 glibc——链接目标平台正确性）
#   A3) seccomp 配置分支实际生效：DT_NEEDED 不得含 libseccomp（本配方
#       显式 -Dseccomp=disabled → src/pledge.c 路径；若 auto 意外探测到
#       系统 libseccomp 则此断言失败，暴露配置不确定性）
#   A4) 真实执行：bin/wob --version 退出 0 且输出 "wob version 0.16"
#       —— HMFS 未签名 ELF 执行 EPERM、动态依赖（libwayland-client）
#       解析失败都会在这一步暴露
#   A5) 真实执行：bin/wob --help 输出 usage（"Usage: wob"）
#
# 用法：test_wob_ohos.sh <pkg_dir> [wayland_libdir]
set -eu

if [ $# -lt 1 ]; then
    echo "FAIL: 用法: test_wob_ohos.sh <pkg_dir> [wayland_libdir]" >&2
    exit 1
fi
PKG="$1"
WLLIB="${2:-}"
WOB="$PKG/bin/wob"
[ -f "$WOB" ] || { echo "FAIL: $WOB 缺失"; exit 1; }

RE=""
for cand in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf; do
    if command -v "$cand" >/dev/null 2>&1; then RE="$cand"; break; fi
    if [ -x "$cand" ]; then RE="$cand"; break; fi
done
[ -n "$RE" ] || { echo "FAIL: 无 readelf/llvm-readelf 可用"; exit 1; }

# A1: AArch64 ELF
"$RE" -h "$WOB" | grep -q "AArch64" || {
    echo "FAIL A1: bin/wob 非 AArch64 ELF"; exit 1; }
echo "PASS A1: ELF Machine = AArch64"

# A2: musl interpreter（OHOS PC libc 差异）
"$RE" -l "$WOB" | grep -q "ld-musl-aarch64" || {
    echo "FAIL A2: interpreter 非 musl（OHOS PC 必为 ld-musl-aarch64.so.1）"; exit 1; }
echo "PASS A2: musl interpreter (ld-musl-aarch64)"

# A3: seccomp=disabled 分支实际生效
if "$RE" -d "$WOB" | grep -q "libseccomp"; then
    echo "FAIL A3: DT_NEEDED 含 libseccomp —— seccomp=disabled 未生效"
    exit 1
fi
echo "PASS A3: seccomp=disabled 生效（DT_NEEDED 无 libseccomp）"

# A4/A5: 真实执行（签名 / 动态链接闭包）
LD_LIBRARY_PATH="${WLLIB:+$WLLIB:}${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH
"$WOB" --version | grep -q "^wob version 0.16$" || {
    echo "FAIL A4: wob --version 输出异常"; exit 1; }
echo "PASS A4: wob --version 真实执行成功（签名/动态闭包 OK）"

"$WOB" --help | grep -q "Usage: wob" || {
    echo "FAIL A5: wob --help 输出异常"; exit 1; }
echo "PASS A5: wob --help 真实执行成功"

echo "wob OHOS test_package PASS (5 OHOS-specific assertions)"
