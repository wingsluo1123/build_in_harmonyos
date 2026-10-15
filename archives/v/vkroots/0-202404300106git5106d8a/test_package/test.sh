#!/data/service/hnp/bin/bash
# test_package/test.sh — vkroots 消费者验证（OHOS）
#
# R34：真实使用被测头文件。上游 vkroots 是零测试的 header-only 库，故本脚本为
# 适配阶段补全测试，包含**两个消费者用例**：
#   用例 A（集成）：用 vkroots API 编译一个最小的 Vulkan layer 模块（.so）
#   用例 B（端到端）：运行 vkroots_negotiate_e2e 可执行文件，在进程内真实跑通
#                    vkroots 生成的 layer 协商流程（不依赖 loader / GPU / dlopen）
#
# 全部为硬断言：任一失败即 RESULT: FAILED。
#
# 用法: test.sh <layer.so 路径> <e2e 可执行文件路径>
set -u
set -o pipefail
# 注：刻意不启用 `set -e` —— 需在某条断言失败后继续执行剩余断言并汇总计数，
# 失败由 note_fail 显式记账，最终以 FAIL>0 决定退出码。

LAYER="${1:-}"
E2E="${2:-}"
PASS=0
FAIL=0
note_pass() { echo "OK: $*"; PASS=$((PASS + 1)); }
note_fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }

TOUT=""
if command -v timeout >/dev/null 2>&1; then TOUT="timeout 60"; fi

# ── 1. 两个消费者产物都已产出（用例 A / 用例 B）──
if [ -n "$LAYER" ] && [ -f "$LAYER" ]; then
    note_pass "用例A：消费者 layer 编译成功，产物存在: $(basename "$LAYER") ($(wc -c < "$LAYER") 字节)"
else
    note_fail "用例A：未找到消费者 layer 产物（LAYER='$LAYER'）"
fi
if [ -n "$E2E" ] && [ -f "$E2E" ]; then
    note_pass "用例B：端到端消费者可执行文件编译成功，产物存在: $(basename "$E2E") ($(wc -c < "$E2E") 字节)"
else
    note_fail "用例B：未找到端到端消费者可执行文件（E2E='$E2E'）"
fi

# ── 2. OHOS 运行时：拷贝到 HMDFS 工作区并自签名 ──
#    R7/E054/E374：未签名 ELF 首次执行可能被安全机制拦截；
#    CI worker 的 TMPDIR 指向应用沙箱时产物不可执行，故固定在 $HOME/tmp（HMDFS）
mkdir -p "${HOME}/tmp" 2>/dev/null || true
WORK="$(mktemp -d "${HOME}/tmp/vkroots-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
SIGN=""
for c in "$(command -v binary-sign-tool 2>/dev/null || true)" \
         /data/service/hnp/bin/binary-sign-tool \
         /system/bin/binary-sign-tool; do
    if [ -n "$c" ] && [ -x "$c" ]; then SIGN="$c"; break; fi
done

RUNLAYER=""
if [ -n "$LAYER" ] && [ -f "$LAYER" ]; then
    RUNLAYER="$WORK/$(basename "$LAYER")"
    cp "$LAYER" "$RUNLAYER"
    chmod +x "$RUNLAYER" 2>/dev/null || true
fi
RUNE2E=""
if [ -n "$E2E" ] && [ -f "$E2E" ]; then
    RUNE2E="$WORK/e2e_neg"
    cp "$E2E" "$RUNE2E"
    chmod +x "$RUNE2E" 2>/dev/null || true
fi

if [ -n "$SIGN" ]; then
    ok=1
    [ -n "$RUNLAYER" ] && { "$SIGN" sign -inFile "$RUNLAYER" -outFile "$RUNLAYER" -selfSign 1 >/dev/null 2>&1 || ok=0; }
    [ -n "$RUNE2E" ] && { "$SIGN" sign -inFile "$RUNE2E" -outFile "$RUNE2E" -selfSign 1 >/dev/null 2>&1 || ok=0; }
    if [ "$ok" -eq 1 ]; then
        note_pass "OHOS 运行时：两个产物均已自签名并置于 HMDFS 工作区（$SIGN）"
    else
        note_fail "OHOS 运行时：自签名失败（$SIGN）"
    fi
else
    note_pass "OHOS 运行时：未找到 binary-sign-tool，使用未签名产物（已如实记录）"
fi

# ── 3. 目标架构 ──
if command -v file >/dev/null 2>&1; then
    bad=0
    for f in "$RUNLAYER" "$RUNE2E"; do
        [ -n "$f" ] && [ -f "$f" ] || continue
        fout=$(file "$f" 2>&1)
        printf '%s' "$fout" | grep -qiE 'arm64|aarch64' || bad=1
    done
    if [ "$bad" -eq 0 ]; then
        note_pass "产物均为目标架构 arm64"
    else
        note_fail "存在非 arm64 产物"
    fi
else
    note_fail "环境缺少 file 命令，无法校验目标架构"
fi

# ── 4. 用例 A 的 layer 导出入口点（vkroots 生成）──
#   实测依据（readelf -Ws）：vkroots 采用 Vulkan v2 协商接口，只把
#   vkNegotiateLoaderLayerInterfaceVersion 作为动态符号导出；
#   vkGetInstanceProcAddr / vkGetDeviceProcAddr 是经协商结构体交回的函数指针、非导出符号。
if [ -n "$RUNLAYER" ] && [ -f "$RUNLAYER" ] && command -v readelf >/dev/null 2>&1; then
    # 注意：不可写成 `readelf -Ws ... | grep -qF ...` —— grep -q 命中即退出会关闭管道，
    # readelf 收到 SIGPIPE 返回非零，配合本脚本的 set -o pipefail 会把整条管道判为失败。
    # 故先把符号表存进变量，再用 shell 内建 case 匹配（不经外部进程、不建管道）。
    syms=$(readelf -Ws "$RUNLAYER" 2>/dev/null || true)
    case "$syms" in
        *vkNegotiateLoaderLayerInterfaceVersion*)
            note_pass "用例A：layer 模块导出了 vkNegotiateLoaderLayerInterfaceVersion" ;;
        *)
            note_fail "用例A：layer 模块缺少 vkNegotiateLoaderLayerInterfaceVersion" ;;
    esac
else
    note_fail "无法校验 layer 入口点（readelf 缺失或产物不存在）"
fi

# ── 5. 用例 B：端到端运行（真实跑通协商流程，非纯断言）──
if [ -n "$RUNE2E" ] && [ -f "$RUNE2E" ]; then
    ELOG="$WORK/e2e.log"
    $TOUT "$RUNE2E" > "$ELOG" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ] && grep -qF "OK: vkroots end-to-end negotiation passed" "$ELOG"; then
        note_pass "用例B（端到端）：可执行文件实跑通过 —— $(grep -m1 '\[e2e\] vkNegotiate' "$ELOG")"
    else
        note_fail "用例B（端到端）运行失败 rc=$rc，日志: $(tail -3 "$ELOG" | tr '\n' ' ')"
    fi
else
    note_fail "用例B：端到端可执行文件不可用"
fi

# ── 汇总 ──
echo "-----------------------------------------"
echo "vkroots consumer test: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    echo "RESULT: FAILED"
    exit 1
fi
echo "RESULT: PASSED"
exit 0
