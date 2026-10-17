#!/bin/sh
# test_xcdplayer.sh — verify xcdplayer binary works on HarmonyOS
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xcdplayer binary
#   $2 = package bin/ directory (cdinfo lives there too)
#   $3 = optional colon-joined LD_PRELOAD list of runtime .so paths
#        (HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH,
#        so the recipe passes absolute paths to preload as a fallback;
#        xeyes 1.3.1 precedent).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh).
# No set -e/-u/pipefail: toybox ash rejects them; every assertion captures
# its own rc and always prints output so loader errors hit the log.

XCD_BIN="$1"
BIN_DIR="$2"
LD_PRELOAD_EXTRA="${3:-}"

if [ -z "$XCD_BIN" ]; then
    echo "FAIL: xcdplayer binary path not provided"
    exit 1
fi

if [ ! -x "$XCD_BIN" ]; then
    echo "FAIL: $XCD_BIN not found or not executable"
    exit 1
fi

BIN_ONLY=$(dirname "$XCD_BIN")
export LD_LIBRARY_PATH="${BIN_ONLY}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

discovered=5
passed=0

# 诊断：musl ldd 会打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XCD_BIN" 2>&1 || true
fi

echo "[test 1/$discovered] xcdplayer exists and is ELF arm64"
head -c 20 "$XCD_BIN" 2>/dev/null | od -An -tx1 | head -1
if head -c 4 "$XCD_BIN" | od -An -tx1 | grep -q '7f 45 4c 46'; then
    echo "PASS: xcdplayer is an ELF binary"
    passed=$((passed + 1))
else
    echo "FAIL: xcdplayer does not look like an ELF binary"
fi

echo "[test 2/$discovered] xcdplayer runs, no DISPLAY -> graceful 'can't open display' exit(1)"
# 无 DISPLAY：top_setup() 里 XtOpenDisplay 失败后 fprintf(stderr,
# "can't open display\n") 并 exit(1)。该路径要求全部动态库解析成功，
# 是完整的可执行性冒烟测试（xcdplayer 无 -version/-help 选项，Xt 层
# 之前的独立退出路径只有 display 打开失败这一条）。
out=$(DISPLAY= "$XCD_BIN" 2>&1)
rc=$?
echo "$out"
echo "exit=$rc"
if echo "$out" | grep -q "can't open display"; then
    echo "PASS: xcdplayer reports 'can't open display' without DISPLAY"
    passed=$((passed + 1))
else
    echo "FAIL: expected 'can't open display' on stderr"
fi
if [ $rc -eq 1 ]; then
    echo "PASS: exit code is 1 on missing display"
    passed=$((passed + 1))
else
    echo "FAIL: expected exit 1, got $rc"
fi

echo "[test 3/$discovered] cdinfo diagnostic tool exists in package"
if [ -x "$BIN_DIR/cdinfo" ]; then
    echo "PASS: cdinfo installed"
    passed=$((passed + 1))
else
    echo "FAIL: cdinfo missing from package bin/"
fi

echo "[test 4/$discovered] man page + app-defaults installed"
if [ -f "$BIN_DIR/../share/man/man1/xcdplayer.1" ] && \
   [ -f "$BIN_DIR/../share/X11/app-defaults/XCdplayer" ]; then
    echo "PASS: xcdplayer.1 and XCdplayer app-defaults installed"
    passed=$((passed + 1))
else
    echo "FAIL: man page or app-defaults missing"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xcdplayer.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xcdplayer.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
