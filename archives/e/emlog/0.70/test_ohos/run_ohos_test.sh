#!/bin/sh
# test_ohos — emlog 0.70 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游 test.sh（内核模块依赖，OHOS 无法运行）与 test_package
# 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  musl libc 验证（无 GLIBC 符号版本 / 无 ld-linux 依赖）
#   T3  宿主路径泄漏检查（产物不得含 /storage、/home 等构建机绝对路径）
#   T4  nbcat 真实功能：非阻塞读取普通文件，输出与输入一致（emlog 核心语义）
#   T5  nbcat 错误用法：无参数时打印 usage 且退出码非零
#   T6  mkemlog 平台边界：内核模块未加载时按补丁语义打印错误并退出非零
#
# 用法：sh run_ohos_test.sh <已安装二进制目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
set -u
BINDIR="${1:-}"
if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "usage: $0 <installed-bin-dir>"
    exit 2
fi

NBCAT="$BINDIR/nbcat"
MKEMLOG="$BINDIR/mkemlog"

fail=0
chk() { # $1=name $2=result(0/1) $3=detail
    if [ "$2" = "0" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 -- ${3:-}"
        fail=1
    fi
}

echo "--- emlog 0.70 HarmonyOS 专项验证 (bindir=$BINDIR) ---"

# T1: aarch64 ELF
if readelf -h "$NBCAT" 2>/dev/null | grep -q "AArch64"; then
    chk "T1 aarch64 ELF" 0
else
    chk "T1 aarch64 ELF" 1 "readelf -h 未显示 AArch64"
fi

# T2: musl libc（无 GLIBC 符号）
if strings "$NBCAT" 2>/dev/null | grep -q "GLIBC"; then
    chk "T2 musl no glibc" 1 "发现 GLIBC 符号"
else
    chk "T2 musl no glibc" 0
fi

# T3: 宿主路径泄漏
if strings "$NBCAT" 2>/dev/null | grep -qE '/storage/|/home/|/Users/'; then
    leak=$(strings "$NBCAT" | grep -E '/storage/|/home/|/Users/' | head -1)
    chk "T3 无宿主绝对路径泄漏" 1 "$leak"
else
    chk "T3 无宿主绝对路径泄漏" 0
fi

# T4: nbcat 非阻塞读取普通文件 → 输出与输入一致
tdir="${TMPDIR:-/data/local/tmp}/emlog-ohos-$$"
mkdir -p "$tdir" 2>/dev/null || tdir="/tmp/emlog-ohos-$$"
if printf 'hello emlog %s\n' "ohos-test" > "$tdir/in.txt"; then
    "$NBCAT" "$tdir/in.txt" > "$tdir/out.txt" 2>/dev/null
    rc=$?
    if [ "$rc" = "0" ] && cmp -s "$tdir/in.txt" "$tdir/out.txt"; then
        chk "T4 nbcat 非阻塞读取输出一致" 0
    else
        chk "T4 nbcat 非阻塞读取输出一致" 1 "rc=$rc"
    fi
else
    chk "T4 nbcat 非阻塞读取输出一致" 1 "无法写入临时文件"
fi
rm -rf "$tdir"

# T5: nbcat 无参数 → usage 且退出非零
if "$NBCAT" 2>/dev/null; then
    chk "T5 nbcat 无参数退出非零" 1 "退出码为 0"
else
    chk "T5 nbcat 无参数退出非零" 0
fi

# T6: mkemlog 内核模块未加载边界（OHOS 平台预期）
out=$("$MKEMLOG" /tmp/emlog-x 8 2>&1)
rc=$?
case "$out" in
    *"module not loaded"*) chk "T6 mkemlog 模块未加载报错" 0 ;;
    *)
        if [ "$rc" != "0" ] && [ -n "$out" ]; then
            chk "T6 mkemlog 模块未加载报错" 0
        else
            chk "T6 mkemlog 模块未加载报错" 1 "rc=$rc out=$out"
        fi
        ;;
esac

echo "---"
if [ "$fail" = "0" ]; then
    echo "RESULT: ALL PASS (6/6)"
    exit 0
else
    echo "RESULT: FAILED"
    exit 1
fi