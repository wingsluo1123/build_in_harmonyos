#!/bin/bash
# HarmonyOS (鸿蒙特有) 端到端消费者用例（rule12）— zyre 2.0.1
# 非纯断言：真实跑通完整功能流（真机 UDP beacon 双节点发现 + JOIN + SHOUT 组播收发）。
# 用法: test_ohos.sh <pkg_lib_dir> <consumer_bin> <work_dir>
#   <pkg_lib_dir>   — 被测包 package_folder/lib（含 libzyre.so）
#   <consumer_bin>  — 消费者程序 test_ohos_flow（test_ohos_flow.c 编译产物）
#   <work_dir>      — 工作目录（消费者在其中产出 flow-report.txt）
set -euo pipefail

LIB_DIR="${1:-}"
CONSUMER="${2:-}"
WORK_DIR="${3:-}"
if [ -z "$LIB_DIR" ] || [ -z "$CONSUMER" ] || [ -z "$WORK_DIR" ]; then
    echo "ERROR: usage: test_ohos.sh <pkg_lib_dir> <consumer_bin> <work_dir>"
    exit 2
fi

fail() { echo "ERROR(HarmonyOS): $*"; exit 1; }

# --- 1. 平台断言：必须在 OpenHarmony 目标上执行（运行时探测，非平台名硬编码）---
case "$(param get const.ohos.fullname 2>/dev/null || true)" in
    OpenHarmony-*) echo "[ok] platform: $(param get const.ohos.fullname)" ;;
    *) fail "this test must run on an OpenHarmony target" ;;
esac

# house E330：OHOS 上无版本化 soname 文件名，包内为单一 lib/libzyre.so
[ -f "$LIB_DIR/libzyre.so" ] || fail "libzyre.so not found at $LIB_DIR/libzyre.so"
[ -x "$CONSUMER" ] || fail "consumer binary not found/executable: $CONSUMER"

# --- readelf 定位（HNP 工具链优先，fallback PATH）---
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then READELF="$cand"; break; fi
done
if [ -z "$READELF" ]; then
    if command -v readelf >/dev/null 2>&1; then
        READELF="$(command -v readelf)"
    elif command -v llvm-readelf >/dev/null 2>&1; then
        READELF="$(command -v llvm-readelf)"
    fi
fi
[ -n "$READELF" ] || fail "readelf not found (HNP toolchain or PATH)"

# --- 2. 产物断言：ELF64 + AArch64 + SONAME（鸿蒙 64 位目标，house E330 契约）---
HDR="$($READELF -h "$LIB_DIR/libzyre.so")"
echo "$HDR" | grep -q "Class:.*ELF64" || fail "libzyre.so: expected ELF64 (64-bit), got: $(echo "$HDR" | grep Class: || true)"
echo "$HDR" | grep -q "Machine:.*AArch64" || fail "libzyre.so: expected EM_AARCH64 (aarch64-linux-ohos), got: $(echo "$HDR" | grep Machine: || true)"
SONAME="$($READELF -d "$LIB_DIR/libzyre.so" 2>/dev/null | grep SONAME | sed 's/.*\[\(.*\)\].*/\1/')"
[ "$SONAME" = "libzyre.so" ] || fail "expected SONAME libzyre.so (E330: no versioned soname on OHOS), got: '$SONAME'"
echo "[ok] libzyre.so: ELF64 / AArch64, SONAME libzyre.so"

CHDR="$($READELF -h "$CONSUMER")"
echo "$CHDR" | grep -q "Class:.*ELF64" || fail "consumer: expected ELF64 (64-bit pointer width)"
echo "$CHDR" | grep -q "Machine:.*AArch64" || fail "consumer: expected EM_AARCH64 (aarch64-linux-ohos triplet)"
echo "[ok] consumer binary: ELF64 / AArch64 (aarch64-linux-ohos)"

# --- 3. 动态依赖闭合：消费者 DT_NEEDED 在 conanrun 环境（LD_LIBRARY_PATH 注入）
#         下全部可解析。注意 CMakeDeps 传递依赖（libzmq/libczmq）以 conan 缓存
#         绝对路径记入 DT_NEEDED 时，运行期按路径直接判存。---
NEEDED="$($READELF -d "$CONSUMER" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/')" || true
[ -n "$NEEDED" ] || fail "no DT_NEEDED entries found in consumer binary"
case "$NEEDED" in
    *libzyre.so*) echo "[ok] consumer links libzyre (DT_NEEDED present)" ;;
    *) fail "consumer does not link libzyre: DT_NEEDED = $NEEDED" ;;
esac
case "$NEEDED" in
    *libzmq.so*) echo "[ok] libzmq dependency present (relative name, no absolute cache path)" ;;
    *) fail "consumer DT_NEEDED lacks libzmq.so: $NEEDED" ;;
esac

LDD=""
for cand in /data/service/hnp/bin/ldd /data/service/hnp/bin/llvm-ldd; do
    if [ -x "$cand" ]; then LDD="$cand"; break; fi
done
if [ -z "$LDD" ] && command -v ldd >/dev/null 2>&1; then
    LDD="$(command -v ldd)"
fi

if [ -n "$LDD" ]; then
    MISSING="$("$LDD" "$CONSUMER" 2>/dev/null | grep -i "not found" || true)"
    if [ -n "$MISSING" ]; then
        fail "dynamic dependencies not closed on OHOS: $MISSING"
    fi
    echo "[ok] dynamic dependency closure: all $(echo "$NEEDED" | wc -l | tr -d ' ') DT_NEEDED libs resolve (ldd)"
else
    # 无 ldd 时按路径扫描闭合。注意 conan test_package 以 /bin/sh 执行本脚本
    # （OHOS /bin/sh 不支持 bash 数组），用 POSIX set -- 位置参数拆分。
    OLDIFS="$IFS"
    IFS=':'
    # shellcheck disable=SC2086
    set -- ${LD_LIBRARY_PATH:-} "$LIB_DIR"
    IFS="$OLDIFS"
    miss=0
    while IFS= read -r lib; do
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|ld-musl*) continue ;;  # 系统 musl 库
        esac
        case "$lib" in
            /*)
                # 绝对路径 DT_NEEDED：conanrun 环境下该路径必然存在，直接判存
                if [ -e "$lib" ]; then
                    continue
                fi
                echo "ERROR(HarmonyOS): NEEDED lib not resolvable: $lib"
                miss=1
                continue
                ;;
        esac
        found=""
        for d in "$@" /system/lib64 /vendor/lib64; do
            [ -n "$d" ] || continue
            if [ -e "$d/$lib" ]; then found="$d/$lib"; break; fi
        done
        if [ -z "$found" ]; then
            echo "ERROR(HarmonyOS): NEEDED lib not resolvable: $lib"
            miss=1
        fi
    done <<ZLIB_LIST
$NEEDED
ZLIB_LIST
    [ "$miss" -eq 0 ] || fail "dynamic dependencies not closed on OHOS"
    echo "[ok] dynamic dependency closure: all DT_NEEDED libs found (path scan)"
fi

# --- 4. 端到端功能流（核心）：真机 UDP beacon 双节点发现 + JOIN 同组 + SHOUT 组播收发 ---
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
"$CONSUMER" "$WORK_DIR" || fail "consumer flow program failed (exit $?)"

# 消费者真实产出的报告文件：存在、非空、含双节点关键步骤与 PASS 结论
[ -s "$WORK_DIR/flow-report.txt" ] || fail "consumer did not produce a non-empty flow-report.txt"
grep -q "ENTER received (peer beta discovered via UDP beacon)" "$WORK_DIR/flow-report.txt" || fail "flow-report missing alpha-side UDP beacon discovery"
grep -q "ENTER received (peer alpha discovered via UDP beacon)" "$WORK_DIR/flow-report.txt" || fail "flow-report missing beta-side UDP beacon discovery"
grep -q "SHOUT hello-from-beta received" "$WORK_DIR/flow-report.txt" || fail "flow-report missing SHOUT reception on alpha"
grep -q "SHOUT ack-from-alpha received" "$WORK_DIR/flow-report.txt" || fail "flow-report missing SHOUT reception on beta"
grep -q "EXIT received (beta stopped after consuming ack)" "$WORK_DIR/flow-report.txt" || fail "flow-report missing alpha-side EXIT handshake (ack consumed by beta)"
grep -q "FLOW-RESULT: PASS" "$WORK_DIR/flow-report.txt" || fail "flow-report does not conclude PASS"
echo "[ok] flow-report.txt produced and verified on disk"

echo "[ok] HarmonyOS-specific consumer flow passed (dual-node UDP beacon discovery + JOIN + SHOUT group flow)"
