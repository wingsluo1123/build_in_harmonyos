#!/bin/sh
# consumer_use_case.sh — mnxdom 3.0.1 消费者用例驱动脚本（自包含）
#
# 消费者用例语义：模拟上层业务组件/应用（「乐谱工程批处理器」），仅通过本包
# 已安装/导出的公开接口（安装前缀下的 <mnxdom/mnxdom.h> 与 libmnxdom.a，
# 及其公共头依赖 nlohmann/json）使用该三方库，验证第三方使用者能够完整跑通
# 一个业务流程并得到可观察结果。不使用库的私有头、不调用内部符号、
# 不复用库自身的测试构建目录。
#
# 用例场景：批处理工具载入一份 MNX 乐谱工程文件 → schema 校验 → 按业务规则
# 补齐小节/声部/排版/分谱 → 导出新的工程文件 → 回读复核业务字段，产出可观察的
# MNX 产物文件与报告行。
# 本脚本自包含完成 编译 → 链接 → 造输入 → 运行 → 核验产物与报告 全链路。
#
# 鸿蒙（OHOS PC/aarch64）环境要点：原生构建（build = host = target），工作目录
# 一律取 $TMPDIR（R10：不得硬编码 /tmp，鸿蒙 /tmp 只读），输入/输出 JSON 文件
# 落在 $TMPDIR 下（HMDFS）。
#
# 用法：sh consumer_use_case.sh <mnxdom-prefix> <nlohmann_json-prefix> [编译器，默认 clang++]
# 退出码：0=全部通过；非 0=失败。
set -u
PREFIX="${1:-}"
JSONPREFIX="${2:-}"
CXX="${3:-clang++}"

[ -n "$PREFIX" ] && [ -d "$PREFIX" ] || {
    echo "usage: $0 <mnxdom-prefix> <nlohmann_json-prefix> [cxx]"; exit 2; }
[ -f "$PREFIX/lib/libmnxdom.a" ] || {
    echo "FAIL: libmnxdom.a not found in $PREFIX/lib"; exit 2; }
[ -f "$PREFIX/lib/libnlohmann_json_schema_validator.a" ] || {
    echo "FAIL: 内嵌的 libnlohmann_json_schema_validator.a not found in $PREFIX/lib"; exit 2; }
[ -f "$JSONPREFIX/include/nlohmann/json.hpp" ] || {
    echo "FAIL: nlohmann/json.hpp not found in $JSONPREFIX/include"; exit 2; }

HERE=$(dirname "$0")
WORK=$(mktemp -d "${TMPDIR:-/tmp}/mnxdom-consumer.XXXXXX") || exit 2
trap 'rm -rf "$WORK"' EXIT

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- 消费者用例 (mnxdom 3.0.1, prefix=$PREFIX) ---"

# ── C0 编译+链接：真实业务程序链接包内静态库 ────────────────────────────────
if "$CXX" -std=c++17 -stdlib=libc++ -O2 \
        -I"$PREFIX/include" -I"$JSONPREFIX/include" \
        "$HERE/consumer_use_case.cpp" \
        "$PREFIX/lib/libmnxdom.a" "$PREFIX/lib/libnlohmann_json_schema_validator.a" \
        -o "$WORK/consumer" 2>"$WORK/cc.log"; then
    chk "C0 消费者程序编译+链接 (libmnxdom.a + 随包交付的 json-schema-validator)" 0
else
    echo "  $(head -5 "$WORK/cc.log")"
    chk "C0 消费者程序编译+链接" 1
fi
[ -f "$WORK/consumer" ] || { echo "--- 消费者用例: FAILED (no binary) ---"; exit $fail; }

# ── 造输入：一份真实 MNX 乐谱工程文件（业务方交给批处理工具的输入）──────────
IN="$WORK/score-project.json"
OUT="$WORK/score-project.out.json"
cat > "$IN" <<'JSON'
{
  "mnx": {
    "version": 1,
    "support": {
      "useAccidentalDisplay": true
    }
  },
  "global": {
    "measures": []
  },
  "parts": []
}
JSON

# ── C1 业务流程执行（真实文件 I/O，工作目录 = $TMPDIR/HMDFS）────────────────
out=$(TMPDIR="$WORK" "$WORK/consumer" "$IN" "$OUT" 2>&1); rc=$?
if [ "$rc" = "0" ]; then
    chk "C1 业务全流程执行 (载入→校验→编辑→导出→回读复核, rc=0)" 0
else
    echo "  rc=$rc"
    echo "$out" | head -5 | sed 's/^/  /'
    chk "C1 业务全流程执行" 1
fi

# ── C2 业务报告行核验（与业务期望值一致：3 小节 / 1 声部 / layout0 / 3/8）──
if echo "$out" | grep -q 'consumer-report: measures=3 parts=1 layout=layout0 first_measure=m1 fraction=3/8'; then
    chk "C2 业务报告与期望一致 (measures=3 parts=1 layout=layout0 fraction=3/8)" 0
else
    echo "$out" | grep 'consumer-report' | sed 's/^/  /'
    chk "C2 业务报告与期望一致" 1
fi

# ── C3 成功标记核验 ─────────────────────────────────────────────────────────
if echo "$out" | grep -q 'consumer-ok'; then
    chk "C3 输出 consumer-ok 成功标记" 0
else
    chk "C3 输出 consumer-ok 成功标记" 1
fi

# ── C4 可观察产物核验：导出的 MNX 工程文件内容是否符合业务预期 ──────────────
if [ -s "$OUT" ]; then
    chk "C4a 导出 MNX 工程文件非空 ($(wc -c < "$OUT" | tr -d ' ') 字节)" 0
else
    chk "C4a 导出 MNX 工程文件非空" 1
fi
if grep -q '"m1"' "$OUT" && grep -q '"layout0"' "$OUT" && grep -q '"Full Score"' "$OUT"; then
    chk "C4b 导出工程含业务补齐的 measure/part/layout/score 结构" 0
else
    chk "C4b 导出工程含业务补齐的结构" 1
fi

echo "--- 消费者用例: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail
