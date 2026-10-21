#!/usr/bin/env sh
# test_package/test.sh — 真实调用 mfiutil 二进制的消费者测试（无需 MegaRAID 硬件）
# 由 test_package/conanfile.py 调用：sh test.sh <path-to-mfiutil>
#
# mfiutil 是 LSI MegaRAID SAS 控制器管理 CLI。测试机（CI runner / 本机
# qemu）上没有 megaraid_sas 驱动与 /dev/megaraid_sas_ioctl_node，因此硬件
# 相关命令必然走设备打开失败路径；纯用户land路径（version / usage /
# 未知命令）可完全确定性地验证：
#   1. 二进制为 ELF（magic 0x7f 'E' 'L' 'F'）
#   2. `version` 返回 0 且输出精确等于 "mfiutil version 1.0.15-rivoreo-r2"
#   3. 无参数 → stderr 打印 Usage 且退出码非 0
#   4. 未知命令 → stderr 报 Unknown command 且退出码非 0
#   5. `show adapter`（无控制器）→ 退出码非 0（Linux ioctl 代码路径被真实执行到设备打开失败）
#   6. 非法选项 -Z → stderr 提示选项错误（OHOS libc 措辞 unrecognized option，glibc 为 invalid option）且退出码非 0
#
# 只验证确定性的用户land行为与失败路径，不依赖任何硬件状态。
# 不触碰 /dev，不在宿主机创建任何文件。
#
# 每个用例独立计数，结束后输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记。
# 任一失败则退出码 1，避免静默通过。
set -u

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-mfiutil>" >&2
    exit 2
fi

bin="$1"
PASS=0
FAIL=0

# ── 用例 1: ELF magic ──
echo "[case 1/6] binary is ELF"
magic=$(head -c 4 "$bin" | od -An -tx1 | tr -d ' \n')
if [ "$magic" = "7f454c46" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] ELF magic 7f454c46"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] unexpected magic: $magic"
fi

# ── 用例 2: version 返回 0 + 输出版本串 ──
echo "[case 2/6] 'version' prints exact version string"
ver_output="$("$bin" version 2>&1)"
rc_v=$?
echo "  rc=$rc_v output: $ver_output"
if [ "$rc_v" -eq 0 ] && [ "$ver_output" = "mfiutil version 1.0.15-rivoreo-r2" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] version string exact"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] rc=$rc_v (expected 0), output mismatch"
fi

# ── 用例 3: 无参数 → Usage + 非 0 ──
echo "[case 3/6] no arguments prints usage and exits non-zero"
noargs_out="$("$bin" 2>&1)"
rc_n=$?
if [ "$rc_n" -ne 0 ] && printf '%s' "$noargs_out" | grep -F "Usage: mfiutil" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] rc=$rc_n, usage printed"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] rc=$rc_n (expected non-zero + usage), got: $(printf '%s' "$noargs_out" | head -1)"
fi

# ── 用例 4: 未知命令 → 非 0 ──
echo "[case 4/6] unknown command errors out"
bad_out="$("$bin" definitely-not-a-command 2>&1)"
rc_b=$?
if [ "$rc_b" -ne 0 ] && printf '%s' "$bad_out" | grep -F "Unknown command" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] rc=$rc_b, Unknown command reported"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] rc=$rc_b, output: $(printf '%s' "$bad_out" | head -1)"
fi

# ── 用例 5: show adapter 无控制器 → 非 0（真实走到设备打开失败）──
echo "[case 5/6] 'show adapter' without controller exits non-zero"
sa_out="$("$bin" show adapter 2>&1)"
rc_s=$?
echo "  rc=$rc_s output: $(printf '%s' "$sa_out" | head -1)"
if [ "$rc_s" -ne 0 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] rc=$rc_s (expected non-zero on a machine without MegaRAID hardware)"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] rc=0 (expected non-zero; unexpected controller present?)"
fi

# ── 用例 6: 非法选项 → 非 0 ──
echo "[case 6/6] invalid option rejected"
opt_out="$("$bin" -Z version 2>&1)"
rc_o=$?
if [ "$rc_o" -ne 0 ] && printf '%s' "$opt_out" | grep -E "invalid option|unrecognized option" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] rc=$rc_o, option error reported"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] rc=$rc_o, output: $(printf '%s' "$opt_out" | head -1)"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <mfiutil-bin>\",\"discovered\":6,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
