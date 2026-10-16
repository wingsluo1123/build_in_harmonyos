#!/usr/bin/env bash
# test_xhk.sh — xhk 1.2 消费者冒烟测试（真实执行打包二进制 + OHOS 平台属性）
#
# 断言：
#   1. bin/xhk 在 conanrun 注入的 PATH 上
#   2. `xhk -v` exit 0 且输出 "xhk, version 1.2"（在 XOpenDisplay 之前）
#   3. `xhk -h` exit 0 且输出 usage（在 XOpenDisplay 之前）
#   4. `xhk -z` 非法选项 exit 1 且输出 usage（选项校验路径）
#   5. ELF 平台属性：AArch64 / OHOS musl 动态链接器 / NEEDED libX11.so.6,
#      libXi.so.6, libXtst.so.6（.codesign 段在签名工具可用时存在）
#
# 刻意不断言 `-t` / 无参 / `-d` 路径：OHOS 无 X server，且上游 aarch64 上有
# 两处真实缺陷（详见 notes.md「上游 aarch64 缺陷」）——
#   (a) `char opt` 在 aarch64 上无符号，`(opt = getopt(...)) != -1` 永真，
#       非 -v/-h/-t 的调用全部落入 default 分支 usage+exit(1)；
#   (b) construct() 在无 X 时返回 NULL，调用点却解引用 screen->display。
# 这两处属上游问题，本适配不引入源码补丁（OHOS 无 X server，运行期功能
# 本就归真机验证），如实记录而不拿它们当通过项。
#
# 本地/CI 模拟运行环境（/opt/ohos-guest）用的是 stock musl，缺 OHOS 硬化
# 符号 __fd_chk（FORTIFY）与 arc4random_buf，制品仓 X11 二进制需要它们。
# 该 guest rootfs 自带 shim；真机 OHOS libc 本身提供这些符号，shim 不存在时
# 自动跳过（配方本体不依赖 shim）。
set -uo pipefail

echo "--- xhk consumer verification (OHOS aarch64) ---"
pass=0
fail=0
ok()  { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }

PRELOAD=""
for s in /opt/ohos-guest/lib/libfdchkshim.so /opt/ohos-guest/lib/libarc4shim.so; do
    if [ -f "$s" ]; then
        PRELOAD="${PRELOAD:+$PRELOAD:}$s"
    fi
done
if [ -n "$PRELOAD" ]; then
    echo "guest shims: $PRELOAD"
fi

BIN="$(command -v xhk || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: xhk not on PATH (conanrun did not inject package bin/)"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xhk.sh","discovered":0,"passedCount":0}\n'
    exit 1
fi
echo "binary: $BIN"

# LD_PRELOAD 只作用于被测 aarch64 二进制（经 env 传递），不影响 host 侧
# timeout/coreutils，避免 host ld.so 对 aarch64 shim 的噪声告警。
run_bin() {
    if [ -n "$PRELOAD" ]; then
        timeout 30 env LD_PRELOAD="$PRELOAD" "$BIN" "$@"
    else
        timeout 30 "$BIN" "$@"
    fi
}

# ── 1. 版本路径 ────────────────────────────────────────────────────
out="$(run_bin -v 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'xhk, version 1.2'; then
    ok "'xhk -v' exit 0 and prints 'xhk, version 1.2'"
else
    bad "'xhk -v' rc=$rc output=$(printf '%s' "$out" | head -3 | tr '\n' ' ')"
fi

# ── 2. 用法路径 ────────────────────────────────────────────────────
out="$(run_bin -h 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qi 'usage:'; then
    ok "'xhk -h' exit 0 and prints usage"
else
    bad "'xhk -h' rc=$rc output=$(printf '%s' "$out" | head -3 | tr '\n' ' ')"
fi

# ── 3. 选项校验路径 ────────────────────────────────────────────────
out="$(run_bin -z 2>&1)"
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qi 'usage:'; then
    ok "'xhk -z' (invalid option) exit 1 and prints usage"
else
    bad "'xhk -z' rc=$rc output=$(printf '%s' "$out" | head -3 | tr '\n' ' ')"
fi

# ── 4. ELF / OHOS 平台属性 ─────────────────────────────────────────
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    hdr="$("$READELF" -h "$BIN" 2>/dev/null || true)"
    if printf '%s' "$hdr" | grep -q 'AArch64'; then
        ok "ELF machine = AArch64"
    else
        bad "ELF machine not AArch64: $(printf '%s' "$hdr" | grep -i machine | head -1)"
    fi

    # OHOS 工具链把 musl 解释器写成 /lib/ld-musl-aarch64.so.1 或
    # /lib/ld-linux-aarch64.so.1（两者在 OHOS rootfs 中是同一个 musl 加载器）。
    interp="$("$READELF" -l "$BIN" 2>/dev/null | grep -i 'program interpreter' | head -1)"
    if printf '%s' "$interp" | grep -qE 'ld-(musl|linux)-aarch64'; then
        ok "OHOS musl dynamic loader ($(printf '%s' "$interp" | sed 's/.*interpreter: //; s/\].*//'))"
    else
        bad "unexpected interpreter: $interp"
    fi

    needed="$("$READELF" -d "$BIN" 2>/dev/null | grep -i NEEDED || true)"
    for lib in libX11.so.6 libXi.so.6 libXtst.so.6; do
        if printf '%s' "$needed" | grep -q "$lib"; then
            ok "NEEDED $lib"
        else
            bad "NEEDED missing $lib"
        fi
    done

    if "$READELF" -S "$BIN" 2>/dev/null | grep -q '\.codesign'; then
        ok ".codesign signature segment present (OHOS executable)"
    else
        echo "SKIP: .codesign absent — binary-sign-tool unavailable in this build env"
    fi
else
    echo "SKIP: no llvm-readelf/readelf available"
fi

echo "test xhk 1.2: ${pass} passed, ${fail} failed"
if [ "$fail" -ne 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xhk.sh","discovered":%d,"passedCount":%d}\n' "$((pass + fail))" "$pass"
    exit 1
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xhk.sh","discovered":%d,"passedCount":%d}\n' "$((pass + fail))" "$pass"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xhk 1.2 上游无自动化测试套件：tag archive 无 tests/ 目录；Makefile.am 仅 SUBDIRS=src 与 dist_doc_DATA=README，无 check/test 目标、无 TESTS 变量；configure.ac 仅做编译器探测与 x11/xi/xtst 三个 PKG_CHECK_MODULES，无测试宏"}\n'
exit 0
