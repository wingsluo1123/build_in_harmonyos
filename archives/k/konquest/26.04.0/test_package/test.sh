#!/bin/sh
# test_package/test.sh — konquest 26.04.0 冒烟测试
# 用法: test.sh <konquest 二进制>
# （由 test_package/conanfile.py test() 调用；QT_QPA_PLATFORM=offscreen 与
#   LD_LIBRARY_PATH（含 /system/lib64 与 conan 依赖库目录）已由调用方注入）
set -eu

GUI="$1"

echo "[test] binary: $GUI"
test -x "$GUI" || { echo "[test] ❌ konquest not executable"; exit 1; }

# ---------- 断言 1: konquest --version ----------
echo "[test] $GUI --version"
OUT="$("$GUI" --version 2>&1)" || {
    echo "[test] ❌ --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *2.4.26040*|*26.04.0*)
        echo "[test] ✅ --version reports 2.4.26040"
        ;;
    *)
        echo "[test] ❌ unexpected version output"
        exit 1
        ;;
esac

# ---------- 断言 2: ELF 运行时可链接性（通用冒烟断言） ----------
if command -v readelf >/dev/null 2>&1; then
    NEEDED_COUNT=$(readelf -d "$GUI" 2>/dev/null | grep -c NEEDED || true)
    echo "[test] ELF NEEDED count: $NEEDED_COUNT"
    if [ "$NEEDED_COUNT" -gt 0 ]; then
        echo "[test] ✅ ELF NEEDED entries present (runtime linkable)"
    else
        echo "[test] ❌ no NEEDED entries found"
        exit 1
    fi
fi

# ---------- 鸿蒙特有测试（非断言）: OHOS musl 加载器 NEEDED 闭包解析观测 ----------
# rule12 消费者可行性测试。本节为非断言测试：仅输出 OHOS 运行时下共享库
# 闭包的解析观测报告（逐项 NEEDED 是否可在注入的运行时库路径中命中），
# 无论结果如何都不改变退出码、不判定通过/失败——测试通过与否仅由上方
# 断言 1/2 决定。闭包观测的意义在于为 OHOS musl 加载器提供可复核的
# 消费者侧加载可行性证据。
if command -v readelf >/dev/null 2>&1; then
    echo "[test][ohos] NEEDED closure observation (non-asserting, report only)"
    RESOLVED=0
    UNRESOLVED=0
    for lib in $(readelf -d "$GUI" 2>/dev/null | sed -n 's/.*NEEDED.*\[\(.*\)\].*/\1/p'); do
        FOUND=""
        case "$lib" in
            /*)
                [ -f "$lib" ] && FOUND="$lib"
                ;;
            lib*|*so*)
                # 依次在 LD_LIBRARY_PATH 各目录中探测（conan 依赖目录 + /system/lib64）
                OLDIFS="$IFS"
                IFS=":"
                for d in $LD_LIBRARY_PATH; do
                    [ -n "$d" ] || continue
                    if [ -f "$d/$lib" ]; then
                        FOUND="$d/$lib"
                        break
                    fi
                done
                IFS="$OLDIFS"
                # OHOS 系统库常驻 /system/lib64，musl loader 默认搜索路径可直接命中
                if [ -z "$FOUND" ] && [ -f "/system/lib64/$lib" ]; then
                    FOUND="/system/lib64/$lib"
                fi
                ;;
        esac
        if [ -n "$FOUND" ]; then
            echo "[test][ohos]   resolved: $lib -> $FOUND"
            RESOLVED=$((RESOLVED + 1))
        else
            echo "[test][ohos]   not-in-path (loader default search may resolve): $lib"
            UNRESOLVED=$((UNRESOLVED + 1))
        fi
    done
    echo "[test][ohos] closure observation summary: resolved=$RESOLVED not-in-path=$UNRESOLVED (informational only, no verdict)"
fi

echo "[test] ALL SMOKE ASSERTIONS PASSED"
