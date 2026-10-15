#!/usr/bin/env bash
# HarmonyOS 消费者测试 —— thrax 1.3.10
#
# 上游发布包不含可运行的测试套件（清点证据见版本目录 notes.md 的「上游测试清点」）：
# src/bin/regression_test.cc 只出现在 EXTRA_DIST 中、不参与构建，且依赖 absl 与
# 未随包分发的 --test_file 语料，`make check` 是空操作。因此本测试从消费者视角
# 走完整链路：
#   1. thraxcompiler 编译无 import 的语法                  → byte.far
#   2. thraxcompiler 编译 import byte.far 的语法           → numbers.far
#   3. thraxcompiler 编译 import byte.far+numbers.far 的语法 → example.far
#   4. thraxrewrite-tester 读回 example.far 改写三行文本，逐条断言输出
#   5. thraxrandom-generator 读回 example.far 随机生成
# 第 3 步是 FST 类型注册表的回归护栏：注册对象被链接器丢弃时，读回 .far 会报
# `Unknown FST type "vector"`，import 语法直接段错误。
set -euo pipefail

compiler="$1"
rewrite_tester="$2"
random_generator="$3"
grammars="$4"
libdir="$5"

test -x "$compiler"
test -x "$rewrite_tester"
test -x "$random_generator"
test -f "$grammars/byte.grm"
test -f "$grammars/example.grm"
test -d "$libdir"

export LD_LIBRARY_PATH="$libdir:${LD_LIBRARY_PATH:-}"

work="$(pwd)/thrax_consumer_test"
rm -rf "$work"
mkdir -p "$work"
cp "$grammars"/*.grm "$grammars"/*.txt "$work"/

# thrax 的 import 相对当前工作目录解析，且 import '.grm' 取同目录同名 .far，
# 因此进入语法目录、按依赖顺序 byte → numbers → example 编译。
cd "$work"

# 1) 无 import 的基础语法
"$compiler" --input_grammar=byte.grm --output_far=byte.far
test -s byte.far

# 2) 依赖 byte.far 的语法
"$compiler" --input_grammar=numbers.grm --output_far=numbers.far
test -s numbers.far

# 3) 同时 import byte.far 与 numbers.far 的语法 —— 运行期必须能查 FST 类型注册表
"$compiler" --input_grammar=example.grm --output_far=example.far
test -s example.far

# 4) 读回 example.far，用 TOKENIZER 规则改写三行输入
rewrite_out="$work/rewrite.out"
{
  printf "Well, I can't eat muffins in an agitated manner.\n"
  printf 'Lieutenant 1840,\n'
  printf 'Mr. Ernest Worthing, B. 4, The Albany.\n'
} | "$rewrite_tester" --far=example.far --rules=TOKENIZER > "$rewrite_out" 2>&1

grep -qF "Well , I ca n't eat muffins in an agitated manner ." "$rewrite_out"
grep -qF "Lieutenant eighteen forty ," "$rewrite_out"
grep -qF "Mr. Ernest Worthing , B. four , The Albany ." "$rewrite_out"
if grep -qF "Unknown FST type" "$rewrite_out"; then
  echo "FAIL: FST type registry is empty (libfst.a registration objects were dropped)" >&2
  exit 1
fi

# 5) 随机生成（读回同一个 .far）
"$random_generator" --far=example.far --rule=TOKENIZER --noutput=2 > "$work/random.out" 2>&1
test -s "$work/random.out"
if grep -qE "Unable to|FATAL|Unknown FST type" "$work/random.out"; then
  echo "FAIL: random generation reported an error" >&2
  cat "$work/random.out" >&2
  exit 1
fi

echo "PASS thrax consumer test: compile + import + rewrite + random generation"
