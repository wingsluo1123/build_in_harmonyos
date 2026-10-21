#!/bin/sh
# test_elf.sh — 鸿蒙消费者用例：打包产物 ELF 结构断言（exec 期）。
# 用法: test_elf.sh <libwlrobs.so 绝对路径>
#
# 平台背景：OHOS PC 对未签名 ELF 的 dlopen/动态映射一律 EACCES
# （E258/E077，binary-sign-tool 签名是唯一通行证）。libwlrobs 的
# DT_NEEDED 闭包（libobs→ffmpeg 等）全部位于依赖包内，整链签名不属
# 本包职责且不可行，故运行期验证采用 ELF 结构断言（readelf，与 CI
# L4 同源工具），证明打包插件是本平台合法的 OBS 插件动态库：
#   1. ELF64 / AArch64（aarch64-linux-ohos 交叉编译产物）
#   2. ET_DYN 共享对象
#   3. DT_NEEDED 声明 libobs.so 与 libwayland-client.so
#   4. .dynsym 导出 OBS 插件契约入口 obs_module_load
set -e

PLUGIN="$1"
if [ -z "$PLUGIN" ] || [ ! -f "$PLUGIN" ]; then
    echo "FAIL: plugin not found: $PLUGIN" >&2
    exit 2
fi

READELF_BIN=$(command -v readelf || command -v llvm-readelf)
if [ -z "$READELF_BIN" ]; then
    READELF_BIN=/data/service/hnp/bin/llvm-readelf
fi

echo "== ELF header =="
"$READELF_BIN" -h "$PLUGIN" | grep -q "ELF64" || { echo "FAIL: not ELF64"; exit 1; }
"$READELF_BIN" -h "$PLUGIN" | grep -q "AArch64" || { echo "FAIL: not AArch64"; exit 1; }
"$READELF_BIN" -h "$PLUGIN" | grep -q "DYN" || { echo "FAIL: not ET_DYN shared object"; exit 1; }
echo "PASS: ELF64 AArch64 ET_DYN"

echo "== DT_NEEDED =="
"$READELF_BIN" -d "$PLUGIN" | grep -q "NEEDED.*libobs\.so" || { echo "FAIL: DT_NEEDED libobs.so missing"; exit 1; }
"$READELF_BIN" -d "$PLUGIN" | grep -q "NEEDED.*libwayland-client\.so" || { echo "FAIL: DT_NEEDED libwayland-client.so missing"; exit 1; }
echo "PASS: DT_NEEDED libobs.so + libwayland-client.so"

echo "== dynsym exports =="
"$READELF_BIN" -W --dyn-syms "$PLUGIN" | grep -q "obs_module_load" || { echo "FAIL: obs_module_load not exported"; exit 1; }
"$READELF_BIN" -W --dyn-syms "$PLUGIN" | grep -q "obs_module_set_pointer" || { echo "FAIL: obs_module_set_pointer not exported"; exit 1; }
echo "PASS: dynsym exports obs_module_load/obs_module_set_pointer"

echo "WLROBS_ELF_STRUCT_OK"
