#!/bin/sh
# test_ohos — tsctp 0.8.6 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OpenHarmony/HarmonyOS, HongMeng Kernel 1.12.0）上对最终
# Conan 包产物做独立专项检查，区别于 test_package 消费者用例（三平台通用口径）：
#
#   T1  aarch64 ELF64 验证（产物可在 OHOS 上加载执行）
#   T2  宿主绝对路径泄漏检查（构建机 /storage、/home 路径不得进入产物）
#   T3  libsctp 静态链入检查（sctp_sendmsg / sctp_recvmsg / sctp_bindx 符号在产物内）
#   T4  SCTP 协议栈能力探测：socket(IPPROTO_SCTP) 是否被内核接受。本机 HongMeng
#       Kernel 无 SCTP 栈 -> 断言 tsctp 优雅报 "Protocol not supported" 且 exit 1
#       （不得崩溃）；若内核带 SCTP 栈则断言服务端能正常监听。
#   T5  上游 CLI 面核验（非法选项 -> 上游 Usage 横幅 + exit 1）
#
# 用法：sh run_ohos_test.sh <已安装 tsctp 路径>
# 退出码：0=全部通过；非 0=有失败（打印首个失败项细节）。
set -u

BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- tsctp HarmonyOS 专项验证 (binary=$BIN) ---"

# --- T1: aarch64 ELF64 ------------------------------------------------------
if command -v readelf >/dev/null 2>&1; then
    readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
else
    # ELF 魔数 7f 45 4c 46 + e_machine=0x00B7(AArch64) 位于偏移 18
    magic="$(od -An -tx1 -N4 "$BIN" 2>/dev/null | tr -d ' \n')"
    mach="$(od -An -tx1 -j18 -N2 "$BIN" 2>/dev/null | tr -d ' \n')"
    [ "$magic" = "7f454c46" ] && [ "$mach" = "b700" ] && r=0 || r=1
fi
chk "T1 aarch64 ELF64 (ELF64 AArch64)" "$r"

# --- T2: 宿主绝对路径泄漏 ---------------------------------------------------
leak="$(grep -a -o -E '/(storage|home)/[^[:space:]]*' "$BIN" 2>/dev/null | head -1)"
if [ -n "$leak" ]; then
    echo "  leak: $leak"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# --- T3: libsctp 静态链入 ---------------------------------------------------
found=0
for sym in sctp_sendmsg sctp_recvmsg sctp_bindx; do
    grep -a -q "$sym" "$BIN" 2>/dev/null && found=$((found + 1)) || echo "  missing: $sym"
done
[ "$found" = "3" ] && r=0 || r=1
chk "T3 静态链入 libsctp ($found/3 符号)" "$r"

# --- T4: SCTP 协议栈能力探测 ------------------------------------------------
PORT=$((20000 + ($$ % 20000)))
if command -v timeout >/dev/null 2>&1; then TO="timeout 8"; else TO=""; fi
# shellcheck disable=SC2086
out="$($TO "$BIN" -L 0.0.0.0 -p "$PORT" 2>&1)"
rc=$?
case "$rc" in
    139|134|136|135|132)
        echo "  CRASH: rc=$rc out=[$out]"
        r=1
        ;;
    *)
        case "$out" in
            *"Protocol not supported"*|*"Address family not supported"*)
                # 本机 HongMeng Kernel 无 SCTP 栈：优雅失败（tsctp 错误路径 exit 1）
                [ "$rc" = "1" ] && r=0 || r=1
                echo "  note: 本机内核无 SCTP 栈（EPROTONOSUPPORT），tsctp 优雅报错 rc=$rc"
                ;;
            *)
                if [ "$rc" = "124" ] || [ "$rc" = "0" ]; then
                    echo "  note: 内核 SCTP 栈可用，服务端已监听 0.0.0.0:$PORT"
                    r=0
                else
                    echo "  rc=$rc out=[$out]"
                    r=1
                fi
                ;;
        esac
        ;;
esac
chk "T4 SCTP 协议栈探测（无崩溃，行为符合平台能力）" "$r"

# --- T5: 上游 CLI 面 -------------------------------------------------------
out="$("$BIN" -Z 2>&1)"
rc=$?
if [ "$rc" = "1" ] \
   && echo "$out" | grep -qF "Usage: tsctp [options] [address]" \
   && echo "$out" | grep -qF -- "-p port"; then
    r=0
else
    r=1
    echo "  rc=$rc out=[$out]"
fi
chk "T5 上游 CLI 用法横幅 + exit 1" "$r"

echo "--- tsctp OHOS 专项: $([ "$fail" = "0" ] && echo ALL PASS || echo FAILED) ---"
exit "$fail"
