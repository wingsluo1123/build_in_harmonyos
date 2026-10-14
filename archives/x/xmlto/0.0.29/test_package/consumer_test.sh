#!/bin/sh
# xmlto 0.0.29 —— 消费者端到端用例（HarmonyOS PC）
#
# 用法: consumer_test.sh <bindir>
#
# 覆盖两部分（每一步都校验退出码，非 Python assert）：
#
#  A. HarmonyOS 专有非断言检查 —— 原生 ELF 与动态依赖闭包加载
#     A1 xmlif 必须是 OHOS aarch64 原生 ELF 可执行文件
#     A2 xmlif 的 DT_NEEDED 闭包必须存在且含 libc.so
#     A3 闭包在本机真实加载：原生执行 xmlif，由动态加载器解析整个闭包
#
#  B. 端到端消费者用例（构造输入 -> 真实执行业务 -> 产出结果 -> 校验内容）
#     B1 xmlto 真实转换：XML + 自定义 XSL -> HTML 产物，校验产物内容
#        （需要运行期 xsltproc；环境未提供时明确 SKIP 并记录）
#     B2 xmlif 条件过滤：复现上游手册用例（xmlif/test/test.xml），
#        无条件与 condition=html 两种输入，与上游期望输出逐字节比对
#
# 参数: $1 = 被测包 bin 目录（含 xmlto / xmlif）
set -u

BINDIR="$1"
XMLIF="$BINDIR/xmlif"
XMLTO="$BINDIR/xmlto"
SCRIPT_DIR=$(dirname "$0")

# CI 测试步的 PATH 只有 /system/bin 等基础目录（无 /data/service/hnp/bin），
# 显式补上 hnp 工具目录（readelf / bash）；toybox 的 cmp/mktemp 仍由
# /system/bin 兜底。与 recipe 的 _ohos_env_prefix() 同一口径。
PATH="/data/service/hnp/bin:/system/bin:/bin:$PATH"
export PATH

# xmlto 是 bash 脚本：在 HMDFS（conan 包目录）上直接 execve 脚本受限
# （EACCES/exit 13，或令 worker 挂死），故通过解释器调用。
XMLTO_SH=""
for c in /data/service/hnp/bin/bash /bin/bash bash; do
  if command -v "$c" >/dev/null 2>&1; then XMLTO_SH="$c"; break; fi
done
run_xmlto() {
  if [ -n "$XMLTO_SH" ]; then "$XMLTO_SH" "$XMLTO" "$@"; else "$XMLTO" "$@"; fi
}

[ -x "$XMLIF" ] || { echo "FAIL: 缺少可执行文件 $XMLIF" >&2; exit 1; }
[ -f "$XMLTO" ] || { echo "FAIL: 缺少脚本 $XMLTO" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/xmlto-consumer.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null) \
  || { echo "FAIL: mktemp" >&2; exit 1; }
trap 'rm -rf "$TMP" >/dev/null 2>&1 || true' EXIT INT TERM

fail() { echo "FAIL: $*" >&2; exit 1; }

# ─────────────────────────── A. HarmonyOS 专有检查 ───────────────────────────
echo "== A. HarmonyOS 专有非断言检查：原生 ELF 与动态闭包 =="

echo "+ readelf -h $XMLIF"
readelf -h "$XMLIF"
readelf -h "$XMLIF" | grep -q 'ELF' || fail "A1: xmlif 不是 ELF 可执行文件"
readelf -h "$XMLIF" | grep -q 'AArch64' || fail "A1: xmlif 不是 aarch64 原生 ELF"
echo "+ file $XMLIF"
file "$XMLIF" || true   # 仅作参考输出，不参与判定

echo "+ readelf -d $XMLIF"
readelf -d "$XMLIF"
readelf -d "$XMLIF" | grep -q 'NEEDED' || fail "A2: xmlif 无 DT_NEEDED 动态依赖闭包"
readelf -d "$XMLIF" | grep -q 'libc.so' || fail "A2: xmlif 闭包缺 libc.so"

# A3: 真实加载闭包（不只是静态读取），原生执行 xmlif
"$XMLIF" </dev/null >"$TMP/closure.out" 2>"$TMP/closure.err" \
  || fail "A3: xmlif 原生执行失败（动态闭包在本机不可加载）"
echo "OK A: xmlif 原生 aarch64 ELF，DT_NEEDED 闭包（含 libc.so）在本机真实加载成功"

# ──────────────────────── B1. xmlto 真实转换闭环 ────────────────────────
echo "== B1. 消费者用例：xmlto XML -> HTML 真实转换 =="

if command -v xsltproc >/dev/null 2>&1; then
  mkdir -p "$TMP/b1/out"
  cat > "$TMP/b1/doc.xml" <<'DOC_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<doc><title>HarmonyOS</title><body>xmlto on OHOS works</body></doc>
DOC_EOF
  cat > "$TMP/b1/style.xsl" <<'XSL_EOF'
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <html><body><h1><xsl:value-of select="/doc/title"/></h1><p><xsl:value-of select="/doc/body"/></p></body></html>
  </xsl:template>
</xsl:stylesheet>
XSL_EOF
  echo "+ xmlto -x style.xsl --skip-validation -o out html doc.xml"
  run_xmlto -x "$TMP/b1/style.xsl" --skip-validation -o "$TMP/b1/out" html "$TMP/b1/doc.xml" \
    || fail "B1: xmlto 真实转换失败"
  OUT_FILES=$(ls "$TMP/b1/out" 2>/dev/null | wc -l)
  [ "$OUT_FILES" -ge 1 ] || fail "B1: xmlto 未产出任何文件"
  grep -q '<h1>HarmonyOS</h1>' "$TMP"/b1/out/* || fail "B1: xmlto 产物内容不含预期 <h1>HarmonyOS</h1>"
  echo "OK B1: xmlto 真实转换产物内容校验通过"
else
  echo "SKIP B1: 运行环境未提供 xsltproc（xmlto 的运行期依赖），跳过转换闭环"
fi

# ──────────────────────── B2. xmlif 条件过滤闭环 ────────────────────────
echo "== B2. 消费者用例：xmlif 条件过滤（复现上游手册用例） =="

mkdir -p "$TMP/b2"
cat > "$TMP/b2/input.xml" <<'XMLIF_INPUT_EOF'
Preamble
<!-- this is the test on the manual page -->
Always issue this text.
<?xmlif if condition='html'?>
Issue this text if 'condition=html' is given on the command line.
<?xmlif elif condition='pdf|ps'?>
Issue this text if 'condition=pdf' or 'condition=ps'
is given on the command line.
<?xmlif else?>
Otherwise issue this text.
<?xmlif fi?>
Always issue this text.
<!-- this ends the test on the manual page -->
<?xmlif if condition='foo'?>
Should display only if condition is foo
<?xmlif elif condition='baz'?>
Should display only if condition is baz
<?xmlif else?>
Should display only if condition is not foo and not baz
<?xmlif fi?>
<?xmlif if not condition='bar'?>
Should display only if condition is not bar
<?xmlif if cond2='on'?>
This should be displayed only when cond2 is on.
<?xmlif fi?>
<?xmlif else?>
Should display only if condition is bar
<?xmlif fi?>
Postamble.
XMLIF_INPUT_EOF
cat > "$TMP/b2/expected-no-condition" <<'XMLIF_EXP_NC_EOF'
Preamble
<!-- this is the test on the manual page -->
Always issue this text.






Otherwise issue this text.

Always issue this text.
<!-- this ends the test on the manual page -->





Should display only if condition is not foo and not baz


Should display only if condition is not bar






Postamble.
XMLIF_EXP_NC_EOF
cat > "$TMP/b2/expected-html" <<'XMLIF_EXP_HTML_EOF'
Preamble
<!-- this is the test on the manual page -->
Always issue this text.

Issue this text if 'condition=html' is given on the command line.






Always issue this text.
<!-- this ends the test on the manual page -->





Should display only if condition is not foo and not baz


Should display only if condition is not bar






Postamble.
XMLIF_EXP_HTML_EOF

echo "+ xmlif < input.xml > out-no-condition"
"$XMLIF" < "$TMP/b2/input.xml" > "$TMP/b2/out-no-condition" || fail "B2: xmlif 无条件执行失败"
cmp "$TMP/b2/expected-no-condition" "$TMP/b2/out-no-condition" \
  || fail "B2: xmlif 无条件输出与上游期望不一致"

echo "+ xmlif condition=html < input.xml > out-html"
"$XMLIF" condition=html < "$TMP/b2/input.xml" > "$TMP/b2/out-html" || fail "B2: xmlif condition=html 执行失败"
cmp "$TMP/b2/expected-html" "$TMP/b2/out-html" \
  || fail "B2: xmlif condition=html 输出与上游期望不一致"

echo "OK B2: xmlif 条件过滤两种输入均与上游期望逐字节一致"
echo "ALL CONSUMER TESTS PASSED"
