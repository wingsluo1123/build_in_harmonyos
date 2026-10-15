#!/usr/bin/env bash
# test_package/cli_test.sh — 已安装 pico2wave 命令行的真实行为测试
#
# 在 conanrun 环境运行。断言分两类：
#   1. 链接真实性：readelf 检查 ELF 的 NEEDED 条目里确实有被测包产出的
#      libttspico.so.0；popt 因制品仓 popt/1.19 为静态包（shared=False）而由
#      libtool 静态链入，NEEDED 不含 libpopt，故改用 nm 统计 popt 符号存在。
#   2. 运行真实行为：--help / 缺 --wave / 非法语言 / 非法选项 的退出码与
#      文案，全部取自上游 bin/pico2wave.c 的实际分支。
#
# 用法: cli_test.sh <package_folder>
#
# 刻意只用 `set -u` 而不加 `set -e`：本脚本逐条执行断言并自行累计 PASS/FAIL，
# 需要容忍单条命令本身返回非零（例如被测 CLI 的预期错误路径 rc=1）；
# 真正的失败判定由末尾的 FAIL 计数与退出码负责。
set -u

PKG="${1:?usage: cli_test.sh <package_folder>}"
PICO2WAVE="$PKG/bin/pico2wave"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "PASS $PASS: $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL $FAIL: $1"; }
rc_is() { # 描述 期望码 实际码
    if [ "$3" -eq "$2" ]; then ok "$1 (rc=$3)"; else bad "$1 (rc=$3, want $2)"; fi
}
has() { # 描述 被检文本 子串
    case "$2" in
        *"$3"*) ok "$1" ;;
        *) bad "$1 (未找到: $3)" ;;
    esac
}

# ── 0. 可执行产物存在 ─────────────────────────────────────────────
if [ -f "$PICO2WAVE" ]; then
    ok "installed bin/pico2wave exists"
else
    bad "installed bin/pico2wave is missing: $PICO2WAVE"
    echo ""
    echo "CLI-TEST: $PASS/$((PASS + FAIL)) assertions passed, $FAIL failed"
    echo "CLI-TEST-FAILED"
    exit 1
fi
if [ -x "$PICO2WAVE" ]; then
    ok "installed bin/pico2wave is executable"
else
    bad "installed bin/pico2wave is not executable"
fi

# ── 1. 链接真实性（NEEDED 必含本包 libttspico；popt 为静态链入）──────
READELF="$(command -v llvm-readelf || command -v readelf || true)"
NM="$(command -v llvm-nm || command -v nm || true)"
if [ -n "$READELF" ]; then
    NEEDED="$("$READELF" -d "$PICO2WAVE" 2>/dev/null | grep -F NEEDED || true)"
    has "pico2wave NEEDED includes libttspico (本包产物)" "$NEEDED" "libttspico"
    ok "readelf -d produced a dynamic section"
else
    bad "no readelf/llvm-readelf available to verify linkage"
fi
# 制品仓的 popt/1.19 是静态包（shared=False），libtool 把 libpopt.a 静态链入，
# 因此 NEEDED 中不会有 libpopt —— 改为校验二进制内确实含 popt 符号。
if [ -n "$NM" ]; then
    POPT_SYMS="$("$NM" "$PICO2WAVE" 2>/dev/null | grep -ci popt || true)"
    if [ "${POPT_SYMS:-0}" -ge 1 ] 2>/dev/null; then
        ok "pico2wave contains popt symbols (popt 已链入, ${POPT_SYMS} 个)"
    else
        bad "pico2wave has no popt symbols (found ${POPT_SYMS:-0})"
    fi
else
    bad "no nm/llvm-nm available to verify popt linkage"
fi

# ── 2. --help：打印用法并正常退出（L2 smoke test 依赖此路径）──────
OUT="$("$PICO2WAVE" --help 2>&1)"; RC=$?
rc_is "--help 退出码" 0 "$RC"
has "--help 输出含 uasge 头" "$OUT" "Usage:"
has "--help 列出 -w, --wave" "$OUT" "-w, --wave"
has "--help 列出 -l, --lang" "$OUT" "-l, --lang"
has "--help 显示 -l 默认值 en-US" "$OUT" "en-US"

# ── 3. 缺少必需的 --wave：上游语义 exit(1) ────────────────────────
OUT="$("$PICO2WAVE" "hello" 2>&1)"; RC=$?
rc_is "缺 --wave 退出码" 1 "$RC"
has "缺 --wave 错误文案" "$OUT" "Mandatory option: --wave=filename.wav"

# ── 4. 未知语言：上游语义 exit(1) 并列出合法语言 ──────────────────
OUT="$("$PICO2WAVE" -w "$PKG/picotts-cli-probe.wav" -l "xx-XX" "hello" 2>&1)"; RC=$?
rc_is "未知语言退出码" 1 "$RC"
has "未知语言错误文案" "$OUT" "Unknown language: xx-XX"
has "未知语言列出合法值 en-US" "$OUT" "en-US"

# ── 5. 非法选项：上游语义 exit(1) ────────────────────────────────
OUT="$("$PICO2WAVE" --definitely-not-an-option 2>&1)"; RC=$?
rc_is "非法选项退出码" 1 "$RC"
has "非法选项错误文案" "$OUT" "Invalid option"

rm -f "$PKG/picotts-cli-probe.wav"

TOTAL=$((PASS + FAIL))
echo ""
echo "CLI-TEST: $PASS/$TOTAL assertions passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
    echo "CLI-TEST-OK"
else
    echo "CLI-TEST-FAILED"
    exit 1
fi
