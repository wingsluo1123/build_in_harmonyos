#!/bin/sh
# test_ohos — nibbleandahalf 0.0-git-c3d5edba42 HarmonyOS PC 专项验证（自包含）
#
# 在真实鸿蒙 PC（aarch64, OHOS, clang 15）上对已安装 Conan 包做独立专项检查，
# 区别于上游自带测试（testbase64.c 随机字符串往返）与 test_package 消费者用例：
#
#   T0  包内制品定位（include/base64.h + lib/libnaah64.a 存在）
#   T1  aarch64 ELF 验证（静态库成员为 ELF64 AArch64 目标文件，可在 OHOS 链接执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  真实 OHOS 专项用例运行：ohos_test.c 经 clang + 已安装包编译链接并执行，
#       覆盖含 NUL 二进制往返 / 16MB 大块往返 / 坏 ASCII 拒绝 / 坏长度安全 / 空输入
#
# 用法：sh run_ohos_test.sh [已安装包根目录]
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
PKG="${1:-}"
CC="${OHOS_CC:-/data/service/hnp/bin/clang}"
[ -n "$PKG" ] || { echo "usage: $0 <installed-package-root>"; exit 2; }
[ -f "$PKG/include/base64.h" ] || { echo "FAIL: $PKG/include/base64.h not found"; exit 2; }
[ -f "$PKG/lib/libnaah64.a" ] || { echo "FAIL: $PKG/lib/libnaah64.a not found"; exit 2; }
[ -x "$CC" ] || { echo "FAIL: clang not found: $CC"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- nibbleandahalf HarmonyOS 专项验证 (pkg=$PKG) ---"

# T0: 包内制品
[ -f "$PKG/include/base64.h" ] && [ -f "$PKG/lib/libnaah64.a" ] && r=0 || r=1
chk "T0 包内制品完整 (include+lib)" "$r"

# T1: 静态库成员为 aarch64 目标文件
if ar p "$PKG/lib/libnaah64.a" base64.o 2>/dev/null | file - | grep -qiE "arm64|aarch64|AArch64"; then
    chk "T1 libnaah64.a 成员为 ELF64 AArch64" 0
else
    chk "T1 libnaah64.a 成员为 ELF64 AArch64" 1
fi

# T2: 宿主路径泄漏（构建机 /storage /home 绝对路径不得进入包内文本）
if strings "$PKG/lib/libnaah64.a" "$PKG/include/base64.h" 2>/dev/null | grep -qE '/storage/|/home/|/Users/'; then
    echo "  leak: $(strings "$PKG/lib/libnaah64.a" "$PKG/include/base64.h" | grep -E '/storage/|/home/|/Users/' | head -1)"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 编译并运行 OHOS 专项用例
SRC="$(dirname "$0")/ohos_test.c"
BIN="$(dirname "$0")/ohos_test_bin"
"$CC" -O2 -I"$PKG/include" "$SRC" -L"$PKG/lib" -lnaah64 -o "$BIN" 2>/dev/null
if [ ! -x "$BIN" ]; then
    echo "  compile failed"
    chk "T3 编译 ohos_test.c" 1
else
    if file "$BIN" | grep -qiE "arm64|aarch64|AArch64"; then
        chk "T3a 编译产物为 ELF64 AArch64" 0
    else
        chk "T3a 编译产物为 ELF64 AArch64" 1
    fi
    out=$(timeout 60 "$BIN" 2>&1); rc=$?
    if [ "$rc" = "0" ]; then
        echo "$out" | grep -q "ALL PASS" && r=0 || r=1
        chk "T3b 专项用例运行 (exit=0 且 ALL PASS)" "$r"
    else
        echo "  rc=$rc out=$(echo "$out" | tail -3 | tr '\n' ' ')"
        chk "T3b 专项用例运行" 1
    fi
    rm -f "$BIN"
fi

echo "--- nibbleandahalf OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
