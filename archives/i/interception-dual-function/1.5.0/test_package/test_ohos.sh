#!/usr/bin/env bash
# HarmonyOS-specific test for interception-dual-function 1.5.0.
#
# 断言（仅对 OHOS 目标有意义）：
#   1) 交付 ELF 是 ELF64 / AArch64 对象
#   2) 解释器为 musl（ld-musl-aarch64.so.1），即真正的 OHOS/musl 目标
#   3) NEEDED 无 Linux-only 条目（libutil 等），且按配方声明动态依赖 libevdev
#   4) 二进制能在 OHOS 上真实执行（-v 输出 1.5.0）
#   5) calloc(0) 回归探针：上游 build_tap()/build_hold() 对标量 YAML 节点
#      误用 Node::size()（yaml-cpp 对标量返回 0），calloc(0, sizeof(Mapping))
#      后写 ->code 越界。glibc 的 calloc(0) 返回块足够大而掩盖该缺陷，OHOS
#      musl 下必崩（SIGSEGV）。以真实 input_event 流跑一次 tap 序列，要求
#      退出码 0 且输出 4 个按键事件——补丁回归即在此步炸掉。
set -u
BIN_DIR="$1"
BIN="$BIN_DIR/dual-function-keys"
HERE="$(cd "$(dirname "$0")" && pwd)"
fails=0

ok()   { echo "ok   - $1"; }
fail() { echo "FAIL - $1" >&2; fails=$((fails + 1)); }

READELF="${READELF:-}"
if [ -z "$READELF" ] || ! command -v "$READELF" >/dev/null 2>&1; then
    for c in llvm-readelf /data/service/hnp/bin/llvm-readelf readelf; do
        if command -v "$c" >/dev/null 2>&1; then READELF="$c"; break; fi
    done
fi

# 1) ELF64 / AArch64
hdr="$("$READELF" -h "$BIN" 2>/dev/null || true)"
if echo "$hdr" | grep -q "ELF64" && echo "$hdr" | grep -q "AArch64"; then
    ok "dual-function-keys is ELF64/AArch64"
else
    fail "dual-function-keys is not an ELF64/AArch64 object"
fi

# 2) musl interpreter (OHOS target identity)
interp="$( ( "$READELF" -l "$BIN" 2>/dev/null || true) | grep -o 'ld-musl[^]]*' | head -1)"
if echo "$interp" | grep -q "ld-musl-aarch64"; then
    ok "interpreter is musl ($interp)"
else
    fail "interpreter is not musl (got: ${interp:-none})"
fi

# 3) NEEDED entries: dynamic libevdev expected, no Linux-only libs
needed="$("$READELF" -d "$BIN" 2>/dev/null || true)"
if echo "$needed" | grep -q "libevdev.so"; then
    ok "NEEDED contains libevdev.so (yaml-cpp linked statically)"
else
    fail "libevdev.so missing from NEEDED entries"
fi
if echo "$needed" | grep -qE "libutil|librt\.so"; then
    fail "Linux-only NEEDED entry present"
else
    ok "no Linux-only dynamic dependencies"
fi

# 4) runs on OHOS
if v="$("$BIN" -v 2>&1)" && echo "$v" | grep -q "1.5.0"; then
    ok "executes on OHOS ($v)"
else
    fail "did not execute on OHOS"
fi

# 5) calloc(0) regression probe (scalar TAP/HOLD mapping, tap sequence)
if python3 - "$BIN" "$HERE/cfg.yaml" <<'PY'
import struct, subprocess, sys
binary, cfg = sys.argv[1], sys.argv[2]
ev = lambda s, u, t, c, v: struct.pack("<qqHHi", s, u, t, c, v)
data = ev(0, 0, 1, 42, 1) + ev(0, 50_000, 1, 42, 0)  # KEY_LEFTSHIFT press+release
p = subprocess.run([binary, "-c", cfg], input=data,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert p.returncode == 0, f"exit={p.returncode} stderr={p.stderr!r}"
keys = [struct.unpack("<qqHHi", p.stdout[i:i + 24])[2:]
        for i in range(0, len(p.stdout), 24)]
keys = [k for k in keys if k[0] == 1]
expected = [(1, 42, 1), (1, 42, 0), (1, 111, 1), (1, 111, 0)]
assert keys == expected, f"expected {expected}, got {keys}"
PY
then
    ok "scalar TAP/HOLD mapping survived on OHOS musl (calloc(0) regression)"
else
    fail "calloc(0) regression probe crashed or produced wrong events"
fi

if [ "$fails" -ne 0 ]; then
    echo "$fails HarmonyOS assertion(s) failed" >&2
    exit 1
fi
echo "all interception-dual-function HarmonyOS assertions passed"
