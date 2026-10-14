#!/usr/bin/env bash
# HarmonyOS-specific test for retro-gtk 1.0.2.
#
# 断言内容（全部针对 OHOS 目标 aarch64-linux-ohos / musl）：
#   1. 包内 ELF（libretro-gtk-1.so.0、retro-runner）都是 ELF64/AArch64 且带
#      .codesign —— OHOS loader 对 dlopen/execve 的硬性要求；
#   2. DT_SONAME 是 libretro-gtk-1.so.0（按名解析，而非路径式 NEEDED）；
#   3. 动态依赖里没有 Linux/glibc 专有条目（libpthread.so.0/librt.so.1/
#      libutil.so.1/libdl.so.2 —— musl 把它们并入 libc）；
#   4. 公开 API 符号导出齐全（消费者与下游真正会用到的那些）；
#   5. include/ 头文件与 pkgconfig/retro-gtk-1.pc 齐备；
#   6. 设备端确定性：用包内 retro-runner 跑一次消费者 + 假核心，视频输出链路
#      （runner → GDBus IPC → memfd 帧缓冲 → RetroPixdata → GdkPixbuf）的整帧
#      校验和必须等于固定值。
set -u

PKG="$1"
BUILD="$2"
RUNNER="$3"

READELF="${READELF:-llvm-readelf}"
fails=0

ok()   { echo "ok   - $1"; }
fail() { echo "FAIL - $1" >&2; fails=$((fails + 1)); }

LIB="$PKG/lib/libretro-gtk-1.so.0"

# 1) ELF64/AArch64 + .codesign
for f in "$LIB" "$RUNNER"; do
    name="$(basename "$f")"
    hdr="$("$READELF" -h "$f" 2>/dev/null)"
    if echo "$hdr" | grep -q "ELF64" && echo "$hdr" | grep -q "AArch64"; then
        ok "$name is ELF64/AArch64"
    else
        fail "$name is not an ELF64/AArch64 object"
    fi
    if "$READELF" -S "$f" 2>/dev/null | grep -q "\.codesign"; then
        ok "$name carries a .codesign section"
    else
        fail "$name has no .codesign section (OHOS loader would refuse it)"
    fi
done

# 2) soname
if "$READELF" -d "$LIB" 2>/dev/null | grep -q "SONAME.*libretro-gtk-1\.so\.0"; then
    ok "SONAME is libretro-gtk-1.so.0 (name-based, not path-based)"
else
    fail "SONAME is not libretro-gtk-1.so.0"
fi

# 3) 无 Linux 专有动态依赖
linux_only=""
for f in "$LIB" "$RUNNER"; do
    if "$READELF" -d "$f" 2>/dev/null | grep -qE "libpthread\.so|librt\.so|libutil\.so|libdl\.so"; then
        linux_only="$linux_only $(basename "$f")"
    fi
done
if [ -z "$linux_only" ]; then
    ok "no Linux-only dynamic dependencies (libpthread/librt/libutil/libdl)"
else
    fail "Linux-only NEEDED entries in:$linux_only"
fi

# 4) 公开 API 符号
for sym in retro_core_new retro_core_boot retro_core_iteration \
           retro_core_get_frames_per_second retro_pixdata_to_pixbuf \
           retro_pixdata_get_width retro_pixdata_get_height; do
    if "$READELF" --dyn-syms "$LIB" 2>/dev/null | grep -q " $sym$"; then
        ok "exports $sym"
    else
        fail "missing exported symbol $sym"
    fi
done

# 5) 头文件 + pkg-config 元数据
for h in retro-gtk.h retro-core.h retro-pixdata.h; do
    if [ -f "$PKG/include/retro-gtk/$h" ]; then
        ok "installs include/retro-gtk/$h"
    else
        fail "missing header include/retro-gtk/$h"
    fi
done
if [ -f "$PKG/lib/pkgconfig/retro-gtk-1.pc" ]; then
    ok "installs lib/pkgconfig/retro-gtk-1.pc"
else
    fail "missing lib/pkgconfig/retro-gtk-1.pc"
fi

# 6) 设备端确定性：消费者 + 假核心 走包内 runner 的整帧校验和
EXPECTED_CHECKSUM="${EXPECTED_CHECKSUM:-0x52f0e94d}"
out="$(RETRO_RUNNER_PATH="$RUNNER" "$BUILD/retro-gtk-consumer" "$BUILD/libretro-test-core.so" 2>&1)"
line="$(echo "$out" | grep '^RETRO_GTK_OHOS_CONSUMER_OK' | head -1)"
if [ -z "$line" ]; then
    fail "consumer did not report success on device: $out"
else
    ok "consumer ran on device: $line"
    checksum="$(echo "$line" | sed -n 's/.*checksum=\(0x[0-9a-f]*\).*/\1/p')"
    if [ "$checksum" = "$EXPECTED_CHECKSUM" ]; then
        ok "on-device frame checksum is deterministic ($checksum)"
    else
        fail "on-device frame checksum $checksum != $EXPECTED_CHECKSUM"
    fi
fi

if [ "$fails" -ne 0 ]; then
    echo "$fails HarmonyOS assertion(s) failed" >&2
    exit 1
fi
echo "all retro-gtk HarmonyOS assertions passed"
