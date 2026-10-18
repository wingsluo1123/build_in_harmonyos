#!/bin/sh
# test_xshogi.sh — 消费者测试：真实执行安装后的 xshogi 二进制
#
# 调用（test_package/conanfile.py test()）:
#   $1 = 包内 xshogi 二进制的绝对路径
#
# POSIX sh only（HMBS [shell_getcwd]：用注入的 SHELL=/bin/sh 执行，不硬编码
# /data/service/hnp/bin/bash；toybox ash 拒绝 set -u/pipefail，故不启用）。
# 每条断言各自捕获退出码并回显输出，方便日志定位 loader 错误。
#
# 本脚本主动清空 LD_LIBRARY_PATH / LD_PRELOAD：设备没有系统 X11 动态库，
# 包必须自包含（依赖 .so 复制进 lib/ + DT_RPATH=$ORIGIN/../lib），裸环境执行成功
# 才算通过；这也与 CI L2（bin/xshogi --version）的裸执行条件一致。
#
# 为什么第 3 条要走 DISPLAY 失效路径：libXt-1.3.1 的选项表里没有
# -help/-version（Initialize.c 只有 -display/-geometry/... 等标准项），
# 上游 xshogi 的 main() 先调 XtAppInitialize（先开 X display）再判 argc，
# 因此除配方补丁添加的 -version 早退外，其余任何调用都会先撞显示连接。
# 用这一点证明二进制真的走到 X11/Xt 初始化。

XSHOGI_BIN="$1"

if [ -z "$XSHOGI_BIN" ]; then
    echo "FAIL: xshogi binary path not provided"
    exit 1
fi

if [ ! -f "$XSHOGI_BIN" ]; then
    echo "FAIL: $XSHOGI_BIN not found"
    exit 1
fi

# 裸环境：清掉可能由外层注入的库搜索路径（自包含性验证的前提）
unset LD_LIBRARY_PATH
unset LD_PRELOAD

echo "[shell] $0"
echo "[bin] $XSHOGI_BIN"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-<unset>}"

if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XSHOGI_BIN" 2>&1 || true
fi

discovered=3
passed=0

# ── test 1/3: --version（裸环境；CI L2 smoke 同一路径）───────────────────
version_output=$("$XSHOGI_BIN" --version 2>&1)
rc=$?
echo "[test 1/$discovered] xshogi --version"
echo "$version_output"
if [ "$rc" -ne 0 ]; then
    echo "FAIL 1: xshogi --version exit=$rc"
else
    case "$version_output" in
        *"xshogi version 1.4.2"*)
            echo "PASS 1: --version reports xshogi version 1.4.2"
            passed=$((passed + 1))
            ;;
        *)
            echo "FAIL 1: unexpected --version output"
            ;;
    esac
fi

# ── test 2/3: -version（单横线形式）──────────────────────────────────────
version_output2=$("$XSHOGI_BIN" -version 2>&1)
rc2=$?
echo "[test 2/$discovered] xshogi -version"
echo "$version_output2"
if [ "$rc2" -ne 0 ]; then
    echo "FAIL 2: xshogi -version exit=$rc2"
else
    case "$version_output2" in
        *"xshogi version 1.4.2"*)
            echo "PASS 2: -version reports xshogi version 1.4.2"
            passed=$((passed + 1))
            ;;
        *)
            echo "FAIL 2: unexpected -version output"
            ;;
    esac
fi

# ── test 3/3: 无效 DISPLAY 下 -help 必须走到 Xt 显示初始化并失败 ──────────
display_output=$(DISPLAY=:987 "$XSHOGI_BIN" -help 2>&1)
rc3=$?
echo "[test 3/$discovered] xshogi -help (DISPLAY=:987)"
echo "$display_output"
if [ "$rc3" -eq 0 ]; then
    echo "FAIL 3: 无效 DISPLAY 下仍退出 0，未走到 Xt 显示初始化"
else
    if echo "$display_output" | grep -i -e 'open display' -e 'invalid display' >/dev/null 2>&1; then
        echo "PASS 3: 非 0 退出且报 Xt 显示失败诊断（证明加载并调用了 X11/Xt）"
        passed=$((passed + 1))
    else
        echo "FAIL 3: rc=$rc3 但输出不是预期的显示失败诊断"
    fi
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xshogi.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xshogi.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
