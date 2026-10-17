#!/bin/sh
# test_parlatype.sh — parlatype 4.3 test_package 消费者验证
#
# 参数：$1 = 被测包的 package_folder（conan 安装后的包根目录）
# 退出码：0 = 全部通过，非 0 = 失败
#
# OHOS 上 parlatype 二进制无法直接执行（XPM exec 要求有效的 .codesign 段，
# 与 ghex 同因），因此这里做实质性静态验证。
#
# 两个关键校验点：
#   * 第 6 项——GStreamer 在 OHOS 上只有静态库，libparlatype 把它链进来后
#     被上游的 libparlatype.map 版本脚本从动态符号表隐藏（readelf -d 看不到
#     libgstreamer-1.0.so.0），必须查 .symtab 才能证明音频引擎真的在二进制里。
#   * 第 8 项——交叉校验：逐个核对可执行文件导入的 pt_* 符号都能在
#     libparlatype 中找到定义，等价于链接期完整性验证。
set -eu
# 注：POSIX sh 无 pipefail，下列管道校验均显式比对输出内容，不依赖管道退出码。

PKG="$1"
if [ -z "$PKG" ]; then
    echo "FAIL: missing package folder argument"
    exit 1
fi
if [ ! -d "$PKG" ]; then
    echo "FAIL: package folder not found: $PKG"
    exit 1
fi

BIN="$PKG/bin/parlatype"
if [ ! -f "$BIN" ]; then
    echo "FAIL: parlatype binary not found: $BIN"
    exit 1
fi
if [ ! -s "$BIN" ]; then
    echo "FAIL: parlatype binary is empty: $BIN"
    exit 1
fi
echo "PASS 1/10: parlatype binary exists ($(wc -c < "$BIN") bytes)"

MAGIC=$(od -An -tx1 -N4 "$BIN" | tr -d ' ')
if [ "$MAGIC" != "7f454c46" ]; then
    echo "FAIL: not an ELF (magic=$MAGIC)"
    exit 1
fi
echo "PASS 2/10: ELF magic OK"

HEADER=$(readelf -h "$BIN" 2>/dev/null)
echo "$HEADER" | grep -q "AArch64" || { echo "FAIL: readelf -h missing AArch64"; exit 1; }
echo "$HEADER" | grep -q "ELF64" || { echo "FAIL: readelf -h missing ELF64"; exit 1; }
echo "PASS 3/10: readelf -h shows AArch64 + ELF64"

DYNAMIC=$(readelf -d "$BIN" 2>/dev/null)
for lib in libparlatype.so.7 libgtk-4.so.1 libadwaita-1.so.0 libgio-2.0.so.0 libglib-2.0.so.0; do
    echo "$DYNAMIC" | grep -q "$lib" || { echo "FAIL: readelf -d missing $lib"; exit 1; }
done
echo "PASS 4/10: readelf -d links libparlatype + GTK4 + libadwaita + GIO/GLib"

LIB=$(ls "$PKG"/lib/libparlatype.so.*.* 2>/dev/null | head -1)
if [ -z "$LIB" ] || [ ! -s "$LIB" ]; then
    echo "FAIL: libparlatype shared object not found under $PKG/lib"
    exit 1
fi
if [ ! -e "$PKG/lib/libparlatype.so.7" ]; then
    echo "FAIL: soname symlink libparlatype.so.7 missing (app links against it)"
    exit 1
fi
readelf -d "$LIB" 2>/dev/null | grep -q "SONAME.*libparlatype.so.7" \
    || { echo "FAIL: $LIB SONAME is not libparlatype.so.7"; exit 1; }
echo "PASS 5/10: $(basename "$LIB") + soname symlink + SONAME libparlatype.so.7"

# GStreamer 音频引擎：静态链接 + 版本脚本隐藏，只能从 .symtab 求证。
# 反向断言先行——静态链入不产生 DT_NEEDED，出现共享依赖即说明并非静态链入。
if echo "$DYNAMIC" | grep -q "libgstreamer-1.0.so.0"; then
    echo "FAIL: readelf -d shows libgstreamer-1.0.so.0 - GStreamer is not statically linked"
    exit 1
fi
# 只统计已定义符号（--defined-only），避免把 `U gst_*` 未解析引用误计为链入证据。
GST_SYMS=$(nm --defined-only "$LIB" 2>/dev/null | grep -c " gst_" || true)
if [ -z "$GST_SYMS" ] || [ "$GST_SYMS" -lt 1000 ]; then
    echo "FAIL: only ${GST_SYMS:-0} defined gst_* symbols in $LIB - GStreamer seems not linked in"
    exit 1
fi
for sym in gst_init gst_element_factory_make gst_pipeline_new; do
    nm --defined-only "$LIB" 2>/dev/null | grep -q " $sym\$" \
        || { echo "FAIL: $sym not defined in $LIB - GStreamer audio engine not linked"; exit 1; }
done
echo "PASS 6/10: GStreamer statically linked ($GST_SYMS defined gst_* symbols incl. gst_init/gst_element_factory_make/gst_pipeline_new; no DT_NEEDED libgstreamer)"

EXPORTED=$(nm -D --defined-only "$LIB" 2>/dev/null | awk '{print $NF}' | grep -c '^pt_' || true)
if [ "$EXPORTED" -lt 60 ]; then
    echo "FAIL: libparlatype exports only $EXPORTED pt_* symbols (expected >= 60)"
    exit 1
fi
for sym in pt_config_new pt_config_get_type pt_player_get_uri pt_waveloader_get_type; do
    nm -D --defined-only "$LIB" 2>/dev/null | grep -q " $sym\$" \
        || { echo "FAIL: libparlatype does not export $sym"; exit 1; }
done
echo "PASS 7/10: libparlatype exports $EXPORTED pt_* symbols incl. core API"

# 交叉校验：可执行文件导入的每个 pt_* 符号都必须由库导出（等价链接期验证）。
IMPORTED=$(nm -D --undefined-only "$BIN" 2>/dev/null | awk '{print $NF}' | grep '^pt_' | sort -u || true)
if [ -z "$IMPORTED" ]; then
    echo "FAIL: binary imports no pt_* symbol from libparlatype"
    exit 1
fi
DEFINED=$(nm -D --defined-only "$LIB" 2>/dev/null | awk '{print $NF}' | sort -u)
UNRESOLVED=""
for sym in $IMPORTED; do
    echo "$DEFINED" | grep -qx "$sym" || UNRESOLVED="$UNRESOLVED $sym"
done
if [ -n "$UNRESOLVED" ]; then
    echo "FAIL: unresolved libparlatype symbols:$UNRESOLVED"
    exit 1
fi
echo "PASS 8/10: all $(echo "$IMPORTED" | wc -l) imported pt_* symbols resolved by libparlatype"

for hdr in parlatype.h pt-config.h pt-player.h pt-waveloader.h pt-waveviewer.h pt-media-info.h; do
    if [ ! -s "$PKG/include/parlatype/$hdr" ]; then
        echo "FAIL: header missing or empty: include/parlatype/$hdr"
        exit 1
    fi
done
echo "PASS 9/10: public headers installed under include/parlatype"

PC=$(find "$PKG" -name parlatype.pc 2>/dev/null | head -1)
if [ -z "$PC" ]; then
    echo "FAIL: parlatype.pc not installed"
    exit 1
fi
grep -q -- "-lparlatype" "$PC" || { echo "FAIL: $PC does not advertise -lparlatype"; exit 1; }
SCHEMA=$(find "$PKG" -name "*.gschema.xml" 2>/dev/null | head -1)
if [ -z "$SCHEMA" ]; then
    echo "FAIL: GSettings schema not installed"
    exit 1
fi
MO=$(find "$PKG/share/locale" -name "parlatype.mo" 2>/dev/null | head -1)
if [ -z "$MO" ]; then
    echo "FAIL: no compiled translation (parlatype.mo) — msgfmt/ITS step produced nothing"
    exit 1
fi
APP=$(find "$PKG/share/applications" -name "*.desktop" 2>/dev/null | head -1)
if [ -z "$APP" ]; then
    echo "FAIL: desktop entry not installed"
    exit 1
fi
echo "PASS 10/10: pkg-config + GSettings schema + compiled translations + desktop entry installed"

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_parlatype.sh","discovered":10,"passedCount":10}'
exit 0
