#!/bin/sh
# test_package 消费者测试 —— xsd/4.0.0
#
# 这是 PR 正文「鸿蒙特有测试」行的唯一取数位置：断言全部作用在**已安装**的
# `bin/xsd` 与包内头文件上，覆盖 xsd 的两种代码生成模式（C++/Tree 常驻内存映射
# 与 C++/Parser 事件流式映射，即 tree/map 双模式），并把**生成出来的代码**真实
# 编译 + 执行（生成代码自测），而不是只断言生成命令 rc=0。
#
# 计数口径：本脚本顶层断言 26 条（A1-A4 / B1-B4 / C1-C6 / D1-D6 / E1-E3 / F1-F3），
# 另 tree-driver 内含 18 条子断言（由 C5 触发、E1/E2 汇总行核对）。末行
# `HMBS_TEST_SUMMARY` 的 discovered = 26 + 18 = 44，failed 为两者之和。
#
# 环境由 test_package/conanfile.py 的 test() 注入：
#   XSD_BIN / XSD_INCLUDE / XERCES_INCLUDE / XERCES_LIB / CXX_BIN
set -u

SRC="$(CDPATH= cd "$(dirname "$0")" && pwd)"
WORK="${TMPDIR:-$SRC}/xsd-tp-$$"
if ! mkdir -p "$WORK" 2>/dev/null; then
  WORK="$SRC/.xsd-tp-$$"
  mkdir -p "$WORK" || exit 9
fi
trap 'rm -rf "$WORK"' EXIT INT TERM

XSD_BIN="${XSD_BIN:-xsd}"
XSD_INCLUDE="${XSD_INCLUDE:-}"
XERCES_INCLUDE="${XERCES_INCLUDE:-}"
XERCES_LIB="${XERCES_LIB:-}"
CXX_BIN="${CXX_BIN:-clang++}"

n=0
failed=0
tree_checks=0
tree_failed=0

# 四个断言辅助函数一律**先 shift 掉描述**再执行命令：`"$@"` 里若带着描述，
# 被执行的第一个词就变成描述的首词（`A1`/`B1`… 都 not found），于是
# ok 恒 FAIL、nok 恒 PASS（假绿）——2026-10-06 实测形态。
ok() {   # ok "<描述>" <命令...>     —— 期望 rc=0
  _desc="$1"; shift
  n=$((n + 1))
  if "$@" >/dev/null 2>&1; then
    echo "ok $n - $_desc"
  else
    failed=$((failed + 1))
    echo "not ok $n - $_desc"
  fi
}

nok() {  # nok "<描述>" <命令...>     —— 期望非零 rc
  _desc="$1"; shift
  n=$((n + 1))
  if "$@" >/dev/null 2>&1; then
    failed=$((failed + 1))
    echo "not ok $n - $_desc (expected non-zero rc)"
  else
    echo "ok $n - $_desc (non-zero rc as expected)"
  fi
}

has() {  # has "<描述>" <文件> <子串>
  _desc="$1"; _file="$2"; _sub="$3"
  n=$((n + 1))
  if grep -q -e "$_sub" "$_file" 2>/dev/null; then
    echo "ok $n - $_desc"
  else
    failed=$((failed + 1))
    echo "not ok $n - $_desc"
  fi
}

out_has() {  # out_has "<描述>" <子串> <命令...>
  _desc="$1"; _sub="$2"; shift 2
  n=$((n + 1))
  if "$@" 2>&1 | grep -q -e "$_sub"; then
    echo "ok $n - $_desc"
  else
    failed=$((failed + 1))
    echo "not ok $n - $_desc"
  fi
}

echo "== A. 工具自报与用法面 =="
ok "A1 xsd --version 退出码为 0" "$XSD_BIN" --version
"$XSD_BIN" --version >"$WORK/version.txt" 2>&1
has "A2 --version 自报 4.0.0" "$WORK/version.txt" "4.0.0"
"$XSD_BIN" --help >"$WORK/help.txt" 2>&1
has "A3 --help 列出 cxx-tree 命令" "$WORK/help.txt" "cxx-tree"
has "A4 --help 列出 cxx-parser 命令" "$WORK/help.txt" "cxx-parser"

echo "== B. 包内交付面 =="
ok "B1 bin/xsd 存在且可执行" test -x "$XSD_BIN"
ok "B2 include/xsd/cxx/tree/elements.hxx 存在" test -f "$XSD_INCLUDE/xsd/cxx/tree/elements.hxx"
ok "B3 include/xsd/cxx/parser/elements.hxx 存在" test -f "$XSD_INCLUDE/xsd/cxx/parser/elements.hxx"
ok "B4 include/xsd/cxx/config.hxx 存在" test -f "$XSD_INCLUDE/xsd/cxx/config.hxx"

echo "== C. C++/Tree（tree）模式：生成 → 编译 → 运行 =="
cp "$SRC/schema.xsd" "$SRC/instance.xml" "$SRC/invalid.xml" \
   "$SRC/bad.xsd" "$SRC/tree-driver.cxx" "$WORK/"
cd "$WORK" || exit 9

ok "C1 xsd cxx-tree 生成树映射" \
  "$XSD_BIN" cxx-tree --std c++11 --generate-ostream --generate-serialization \
  --generate-default-ctor schema.xsd
ok "C2 生成 schema.hxx" test -f "$WORK/schema.hxx"
ok "C3 生成 schema.cxx" test -f "$WORK/schema.cxx"

CXXFLAGS_COMMON="-std=c++11 -O0 -I. -I$XSD_INCLUDE -I$XERCES_INCLUDE"
LDFLAGS_COMMON="-L$XERCES_LIB -lxerces-c -pthread"

ok "C4 编译 tree-driver（消费已安装头 + xerces）" \
  "$CXX_BIN" $CXXFLAGS_COMMON schema.cxx tree-driver.cxx $LDFLAGS_COMMON -o tree-driver
ok "C5 tree-driver 运行成功（正例 + 序列化回写闭环 + 反例拒绝）" \
  "$WORK/tree-driver" "$WORK/instance.xml" "$WORK/invalid.xml" "$WORK/schema.xsd"
if "$WORK/tree-driver" "$WORK/instance.xml" "$WORK/invalid.xml" "$WORK/schema.xsd" \
    >"$WORK/tree.out" 2>/dev/null; then :; fi
tree_checks=$(sed -n 's/^TREE_CHECKS=\([0-9]*\).*/\1/p' "$WORK/tree.out")
tree_failed=$(sed -n 's/.*TREE_FAILED=\([0-9]*\).*/\1/p' "$WORK/tree.out")
tree_checks=${tree_checks:-0}
tree_failed=${tree_failed:-0}
ok "C6 tree-driver 汇总 TREE_FAILED=0" test "$tree_failed" = "0"

echo "== D. C++/Parser（map）模式：生成 → 编译 → 运行 =="
ok "D1 xsd cxx-parser 生成流式映射 + 测试驱动" \
  "$XSD_BIN" cxx-parser --std c++11 --generate-print-impl \
  --generate-test-driver --force-overwrite schema.xsd
ok "D2 生成 schema-pskel.hxx（骨架）" test -f "$WORK/schema-pskel.hxx"
ok "D3 生成 schema-pimpl.cxx（可执行实现）" test -f "$WORK/schema-pimpl.cxx"
ok "D4 编译 parser-driver" \
  "$CXX_BIN" $CXXFLAGS_COMMON schema-pskel.cxx schema-pimpl.cxx \
  schema-driver.cxx $LDFLAGS_COMMON -o parser-driver
ok "D5 合法实例解析成功（rc=0）" "$WORK/parser-driver" "$WORK/instance.xml"
nok "D6 违反 schema 的实例被拒绝（rc!=0）" "$WORK/parser-driver" "$WORK/invalid.xml"

echo "== E. 生成代码的内容断言 =="
has "E1 tree-driver 声明 18 条子断言" "$WORK/tree.out" "TREE_CHECKS=18"
out_has "E2 parser 模式读出 title: Compiler Design" "title: Compiler Design" \
  "$WORK/parser-driver" "$WORK/instance.xml"
out_has "E3 parser 模式读出枚举 Tag: tech" "Tag: tech" \
  "$WORK/parser-driver" "$WORK/instance.xml"

echo "== F. 编译器错误面 =="
ok "F1 xsd version 子命令自报 CodeSynthesis" \
  sh -c "\"$XSD_BIN\" version | grep -q CodeSynthesis"
nok "F2 类型错误的 schema 被拒绝" \
  "$XSD_BIN" cxx-tree bad.xsd
nok "F3 不存在的输入被拒绝" \
  "$XSD_BIN" cxx-tree /nonexistent/no-such.xsd

# tree-driver 的 18 条子断言并入总数（它们与本脚本 26 条是同一消费者面的两层）
total=$((n + tree_checks))
failed_total=$((failed + tree_failed))

echo "== 汇总 =="
echo "HMBS_TEST_SUMMARY discovered=$total passed=$((total - failed_total)) failed=$failed_total skipped=0"
echo "SHELL_ASSERTIONS=$n TREE_SUBASSERTIONS=$tree_checks"

if [ "$failed_total" -ne 0 ]; then
  exit 1
fi
exit 0
