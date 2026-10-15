#!/bin/bash
# test_package consumer test for indi-nightscape
# Verifies the installed INDI driver binary + upstream test tool nstest are
# executable and that the FTDI/libusb dependency chain loads at runtime.
#
# 说明: Nightscape 8300 是真机硬件驱动，CI/本机无硬件；nstest 走到
# libusb_init()/FTDI 扫描即证明二进制可执行、依赖链加载成功
# (无硬件时预期输出 "unable to init ftdi scan device")。
set -u

PKG="$1"
echo "--- indi-nightscape consumer verification (pkg=$PKG) ---"

# 1. 安装产物检查
[ -x "$PKG/bin/indi_nightscape_ccd" ] || { echo "FAIL: bin/indi_nightscape_ccd missing or not executable"; exit 1; }
[ -x "$PKG/bin/nstest" ] || { echo "FAIL: bin/nstest missing or not executable"; exit 1; }
[ -f "$PKG/share/indi/indi_nightscape.xml" ] || { echo "FAIL: share/indi/indi_nightscape.xml missing"; exit 1; }
echo "PASS 1: installed artifacts present (indi_nightscape_ccd, nstest, indi_nightscape.xml)"

# 2. 运行官方上游测试工具 nstest —— 验证二进制可执行且 libftdi/libusb 依赖可加载
# 无硬件时 nstest 的行为因环境 libusb/FTDI 初始化差异而不同：
#   - 本机/部分 CI: "unable to init ftdi scan device: -3 (libusb_init() failed)"
#   - 另一类 CI:   "Found 0 devices / Can't find camera number 0"
# 两者均证明二进制已加载 libftdi/libusb 并走到硬件探测路径。
out=$(timeout 20 "$PKG/bin/nstest" 2>&1)
if echo "$out" | grep -q "unable to init ftdi scan device"; then
    echo "PASS 2: nstest runs and reaches FTDI/libusb init (expected without hardware)"
elif echo "$out" | grep -qE "Found 0 devices|Can't find camera"; then
    echo "PASS 2: nstest runs, finds no Nightscape camera (expected without hardware)"
else
    echo "nstest output=[$out]"
    echo "FAIL: nstest did not reach FTDI/libusb init or camera-scan path"
    exit 1
fi

echo "test indi-nightscape 1.0.6-20221222181314: 2/2 checks PASS"
exit 0