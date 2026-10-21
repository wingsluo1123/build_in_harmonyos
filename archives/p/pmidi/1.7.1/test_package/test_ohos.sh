#!/bin/sh
# 鸿蒙特有测试：验证 pmidi 产物符合 OpenHarmony / HarmonyOS PC (aarch64) 平台不变量。
# 由 test_package/conanfile.py 以 conanrun 环境执行（PATH + LD_LIBRARY_PATH 已注入）。
set -u
fails=0
ok() { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }

# --- 1. 平台断言：本测试必须在 OpenHarmony/HarmonyOS 目标上执行 ---
PLAT="$(param get const.ohos.fullname 2>/dev/null || true)"
if [ -n "$PLAT" ]; then
    case "$PLAT" in
        OpenHarmony-*) ok "platform: $PLAT (OpenHarmony)" ;;
        *) bad "unexpected platform: $PLAT" ;;
    esac
else
    case "$(uname -s 2>/dev/null)" in
        HarmonyOS | OpenHarmony) ok "platform: $(uname -s)" ;;
        *) bad "not an OpenHarmony/HarmonyOS target: $(uname -s) (this test requires the OHOS target)" ;;
    esac
fi

# --- readelf 定位（HNP 工具链优先，回退 PATH）---
READELF=""
for c in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    [ -x "$c" ] && { READELF="$c"; break; }
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
if [ -z "$READELF" ]; then
    bad "readelf not found (HNP toolchain or PATH)"
    echo "$fails HarmonyOS assertion(s) failed"
    exit 1
fi

PMIDI="$(command -v pmidi 2>/dev/null || true)"
if [ -n "$PMIDI" ] && [ -x "$PMIDI" ]; then
    ok "pmidi executable on PATH: $PMIDI"
else
    bad "pmidi not found / not executable on PATH"
    echo "$fails HarmonyOS assertion(s) failed"
    exit 1
fi

# --- 2. ELF 身份：OHOS 目标为 64 位 AArch64 ---
HDR="$("$READELF" -h "$PMIDI")"
echo "$HDR" | grep -q "Class:.*ELF64" && ok "ELF class: ELF64" || bad "expected ELF64"
echo "$HDR" | grep -q "Machine:.*AArch64" && ok "machine: AArch64 (aarch64-linux-ohos)" || bad "expected EM_AARCH64"

# --- 3. 鸿蒙可执行文件必须携带 .codesign 签名段才能被内核加载 ---
if "$READELF" -S "$PMIDI" 2>/dev/null | grep -q "\.codesign"; then
    ok "carries .codesign section"
else
    bad "missing .codesign section (kernel would refuse to exec)"
fi

# --- 4. 动态加载器必须是 OHOS 的 musl loader（而非 glibc ld-linux）---
if "$READELF" -l "$PMIDI" 2>/dev/null | grep -q "ld-musl-aarch64.so.1"; then
    ok "PT_INTERP: ld-musl-aarch64.so.1 (OHOS musl)"
else
    bad "PT_INTERP is not the OHOS musl loader"
fi

# --- 5. 动态依赖闭包 ---
DYN="$("$READELF" -d "$PMIDI" 2>/dev/null | grep NEEDED)"
if echo "$DYN" | grep -Eq "libpthread|libdl\.|librt\.|libutil"; then
    bad "glibc-only NEEDED entry present in OHOS build:"
    echo "$DYN"
else
    ok "no glibc-only NEEDED entries (musl folds pthread/dl/rt into libc)"
fi
echo "$DYN" | grep -q "libasound.so" && ok "links libasound.so (ohpcd alsa-lib)" || bad "libasound.so not in DT_NEEDED"

NEEDED="$(echo "$DYN" | sed 's/.*\[\(.*\)\].*/\1/')"
OLDIFS="$IFS"
IFS=':'
set -- ${LD_LIBRARY_PATH:-}
IFS="$OLDIFS"
miss=0
while IFS= read -r lib; do
    [ -n "$lib" ] || continue
    case "$lib" in libc.so* | ld-musl*) continue ;; esac
    found=""
    for d in "$@" /system/lib64 /vendor/lib64; do
        [ -n "$d" ] || continue
        [ -e "$d/$lib" ] && { found="$d/$lib"; break; }
    done
    if [ -z "$found" ]; then
        echo "  unresolved NEEDED: $lib"
        miss=$((miss + 1))
    fi
done <<EOF
$NEEDED
EOF
if [ "$miss" -eq 0 ]; then
    ok "dynamic dependency closure resolved under conanrun env"
else
    bad "$miss unresolved NEEDED lib(s)"
fi

# --- 6. 平台运行期确认：真实执行产物 ---
OUT="$(pmidi -v 2>&1)"
if [ "$OUT" = "pmidi-1.7.1" ]; then
    ok "runtime: pmidi -v -> $OUT"
else
    bad "runtime version mismatch: $OUT"
fi

if [ "$fails" -ne 0 ]; then
    echo "$fails HarmonyOS assertion(s) failed"
    exit 1
fi
echo "all pmidi HarmonyOS assertions passed"
