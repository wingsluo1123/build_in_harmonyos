#!/bin/sh
# test_package/test_xanalyser.sh — consumer + OHOS-specific test (R34 / L0c).
#
# Usage: sh test_xanalyser.sh <package_folder> [<llvm-readelf>]
#
# xanalyser is a GUI application, so the consumer test executes the packaged
# binary and judges the real output of every step (no assert macros):
#
#   A 打包产物完整性（程序 / man / Motif app-defaults 资源文件）
#   B 鸿蒙特有测试：
#       B1 ELF 解释器为 OHOS musl aarch64 加载器（不是 glibc/x86 产物）
#       B2 ELF Machine = AArch64（armv8 原生，不是交叉产物残留）
#       B3 DT_NEEDED 含完整 Motif/X11 链接链（-lXm -lXt -lXext -lXmu -lXpm -lX11 -lSM -lICE）
#       B4 运行期加载闭包：动态加载器把整条链全部解析（任何缺失会打印
#          "Error loading shared library"）
#       B5 无 X server 时走上游真实 Xt 报错路径：非 0 退出且不挂起
#          （timeout=FAIL，加载器失败 exit 127=FAIL）
#
# Never hangs: every program invocation is wrapped in `timeout`.
set -u

PKG="${1:-}"
READELF="${2:-}"
[ -n "$READELF" ] || READELF="$(command -v llvm-readelf 2>/dev/null || command -v readelf 2>/dev/null || true)"
if [ -n "$READELF" ] && [ ! -x "$READELF" ]; then
    READELF="$(command -v llvm-readelf 2>/dev/null || command -v readelf 2>/dev/null || true)"
fi

A=0
F=0
pass() { A=$((A + 1)); echo "PASS: $1"; }
fail() { A=$((A + 1)); F=$((F + 1)); echo "FAIL: $1"; }

echo "=== xanalyser 1.32 consumer test ==="
echo "package_folder=$PKG"
echo "readelf=$READELF"

if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "FAIL: package folder not found: '${PKG}'"
    echo "assertions=1 failures=1"
    exit 1
fi

BIN="${PKG}/bin/xanalyser"

# ── A1: bin/xanalyser 存在且可执行 ────────────────────────────────────────
if [ -x "$BIN" ]; then
    pass "A1 bin/xanalyser exists and is executable"
else
    fail "A1 bin/xanalyser missing or not executable at ${BIN}"
fi

# ── A2: man page 已安装（上游 doc/Makefile.am man_MANS）────────────────────
if [ -s "${PKG}/share/man/man1/xanalyser.1" ]; then
    pass "A2 share/man/man1/xanalyser.1 installed"
else
    fail "A2 share/man/man1/xanalyser.1 missing or empty"
fi

# ── A3: Motif app-defaults 资源文件（install-data-hook 产物，已归位 share/）──
AD="${PKG}/share/X11/app-defaults/XAnalyser"
if [ -s "$AD" ] && grep -q "XAnalyser.SampleRate" "$AD"; then
    pass "A3 share/X11/app-defaults/XAnalyser installed with XAnalyser.SampleRate resource"
else
    fail "A3 app-defaults resource file missing/empty or without XAnalyser.SampleRate"
fi

# ── B1/B2/B3: ELF 平台属性（鸿蒙特有）────────────────────────────────────
if [ -n "$READELF" ] && [ -x "$BIN" ]; then
    HDR="$("$READELF" -h "$BIN" 2>&1)"
    PROG="$("$READELF" -l "$BIN" 2>&1)"
    DYN="$("$READELF" -d "$BIN" 2>&1)"
    echo "--- captured: $READELF -h (Machine/Class/Type) ---"
    printf '%s\n' "$HDR" | grep -E "Class|Machine|Type" || true
    echo "--- captured: $READELF -l (interpreter) ---"
    printf '%s\n' "$PROG" | grep -i "interpreter" || true
    echo "--- captured: $READELF -d (NEEDED/SONAME) ---"
    printf '%s\n' "$DYN" | grep -E "NEEDED|SONAME" || true
    echo "--- end ---"

    # B1: OHOS musl aarch64 加载器
    if printf '%s\n' "$PROG" | grep -q "ld-musl-aarch64.so.1"; then
        pass "B1 (OHOS) ELF interpreter is the OHOS musl aarch64 loader ld-musl-aarch64.so.1"
    else
        fail "B1 (OHOS) interpreter is not ld-musl-aarch64.so.1"
    fi

    # B2: 原生 aarch64（armv8）产物
    if printf '%s\n' "$HDR" | grep -q "AArch64"; then
        pass "B2 (OHOS) ELF machine is AArch64 (native armv8 build)"
    else
        fail "B2 (OHOS) ELF machine is not AArch64"
    fi

    # B3: 完整 Motif/X11 链接链（上游 LDADD 八个库）
    MISSING=""
    for lib in libXm.so.4 libXt.so.6 libXext.so.6 libXmu.so.6 \
               libXpm.so.4 libX11.so.6 libSM.so.6 libICE.so.6; do
        printf '%s\n' "$DYN" | grep -q "NEEDED.*${lib}" || MISSING="${MISSING} ${lib}"
    done
    if [ -z "$MISSING" ]; then
        pass "B3 DT_NEEDED carries the full Motif/X11 chain (libXm/Xt/Xext/Xmu/Xpm/X11/SM/ICE)"
    else
        fail "B3 DT_NEEDED missing:${MISSING}"
    fi
else
    fail "B1/B2/B3 no usable llvm-readelf/readelf found (got '${READELF}') or binary missing"
fi

# ── B4/B5: 真实执行：加载闭包 + 上游 headless 报错路径 ─────────────────────
RUN_RC=0
RUN_OUT=""
if [ -x "$BIN" ]; then
    RUN_OUT="$(unset DISPLAY; timeout 30 "$BIN" 2>&1)"
    RUN_RC=$?
fi
echo "--- captured: headless xanalyser (DISPLAY unset, timeout 30) exit=${RUN_RC} ---"
printf '%s\n' "$RUN_OUT"
echo "--- end ---"

if printf '%s\n' "$RUN_OUT" | grep -q "Error loading shared library"; then
    fail "B4 (OHOS) dynamic loader could not resolve the Motif/X11 closure"
else
    pass "B4 (OHOS) dynamic loader resolved the packaged Motif/X11/libXpm closure"
fi

if [ "$RUN_RC" -eq 124 ]; then
    fail "B5 headless xanalyser hung (timeout 30 exceeded)"
elif [ "$RUN_RC" -eq 127 ]; then
    fail "B5 headless xanalyser aborted in the dynamic loader (127)"
elif [ "$RUN_RC" -ne 0 ] && printf '%s\n' "$RUN_OUT" | grep -q "Can't open display"; then
    pass "B5 headless xanalyser reached upstream Xt and reported the missing display (exit ${RUN_RC})"
else
    fail "B5 unexpected headless result: exit=${RUN_RC} output='${RUN_OUT}'"
fi

echo "assertions=${A} failures=${F}"
[ "$F" -eq 0 ] || exit 1
exit 0
