#!/bin/sh
# test_xdu.sh — verify xdu binary works on HarmonyOS
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xdu binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#       (libX11.so.6 needs libxcb.so.1/libXau.so.6/libXdmcp.so.6 at runtime;
#        HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#        the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh, do not
# hardcode /data/service/hnp/bin/bash; xeyes/xidle already-passed tests are the
# same pattern). No set -e/-u/pipefail: toybox ash rejects them; every assertion
# captures its own rc and always prints output so loader errors hit the log.
#
# 测试策略: xdu 是 X11 图形工具，无 -version 选项，-help 也在
# XtAppInitialize (xsetup) 之后才处理（xdu.c main()）。无 X server 环境下
# xdu -help 会先走 XtAppInitialize，报 "Can't open display" 并 exit(1) ——
# 这恰好证明 libXaw7/libXt/libXext/libX11 完整动态链接并可加载（缺库时
# loader 会报 "Error loading shared library" + exit 127）。上游无测试套件，
# 本脚本是 R34 实质依赖被测二进制（执行 xdu）的行为验证。

XDU_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XDU_BIN" ]; then
    echo "FAIL: xdu binary path not provided"
    exit 1
fi

if [ ! -x "$XDU_BIN" ]; then
    echo "FAIL: $XDU_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$XDU_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

discovered=3
passed=0

# 诊断：musl ldd 会打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XDU_BIN" 2>&1 || true
fi

echo "[test 1/$discovered] xdu 二进制存在且可执行"
if [ -x "$XDU_BIN" ]; then
    echo "PASS: xdu binary present and executable"
    passed=$((passed + 1))
else
    echo "FAIL: xdu binary not executable"
fi

echo "[test 2/$discovered] xdu -help（无 DISPLAY：XtAppInitialize 报 Can't open display 干净退出，证明动态链接链完整）"
help_output=$("$XDU_BIN" -help 2>&1)
rc=$?
echo "$help_output"
case "$help_output" in
    *"Error: Can't open display"*)
        echo "PASS: xdu -help reached XtAppInitialize (libXaw/libXt/libX11 loaded), rc=$rc"
        passed=$((passed + 1))
        ;;
    *"Error loading shared library"*)
        echo "FAIL: xdu -help loader error (missing runtime library)"
        ;;
    *)
        echo "FAIL: unexpected xdu -help output rc=$rc"
        ;;
esac

echo "[test 3/$discovered] xdu 无参数（stdin 非 tty：同样在 XtAppInitialize 干净退出，证明库加载）"
noarg_output=$("$XDU_BIN" </dev/null 2>&1)
rc=$?
echo "$noarg_output"
case "$noarg_output" in
    *"Error: Can't open display"*)
        echo "PASS: xdu no-arg reached XtAppInitialize, rc=$rc"
        passed=$((passed + 1))
        ;;
    *"Error loading shared library"*)
        echo "FAIL: xdu no-arg loader error (missing runtime library)"
        ;;
    *)
        echo "FAIL: unexpected xdu no-arg output rc=$rc"
        ;;
esac

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xdu.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xdu.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
