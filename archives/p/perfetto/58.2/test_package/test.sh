#!/usr/bin/env bash
# test_package/test.sh — 消费者用例：以真实用户方式调用已安装的 perfetto 工具链。
#
# 只做「消费者行为」校验（平台特有校验见 test_ohos.sh，分开计数，不重复计入）。
# 约束：CI worker 的 PATH 不含 /data/service/hnp/bin、无 curl；只用 bash 内建 + grep -q + readelf。
set -euo pipefail

BIN="${PKG_BIN:-$(dirname "$0")/../bin}"
if command -v trace_processor_shell >/dev/null 2>&1; then
  BIN="$(dirname "$(command -v trace_processor_shell)")"
fi

fails=0
checks=0
note_pass() { checks=$((checks + 1)); echo "PASS $checks: $1"; }
note_fail() { checks=$((checks + 1)); echo "FAIL $checks: $1"; fails=$((fails + 1)); }

# check <name> <cmd> [args...] —— 以 argv 形式直接执行断言（不经 eval，杜绝注入）。
check() {
  local name="$1"
  shift
  if "$@"; then note_pass "$name"; else note_fail "$name"; fi
}

# matches <name> <ERE> <haystack> —— 大小写敏感的子串/正则匹配（haystack 经 stdin 传入，不参与 shell 求值）。
matches() {
  local name="$1" pat="$2" hay="${3:-}"
  if printf '%s\n' "$hay" | grep -Eq -- "$pat"; then note_pass "$name"; else note_fail "$name"; fi
}

# matches_i <name> <ERE> <haystack> —— 同上，但忽略大小写。
matches_i() {
  local name="$1" pat="$2" hay="${3:-}"
  if printf '%s\n' "$hay" | grep -Eqi -- "$pat"; then note_pass "$name"; else note_fail "$name"; fi
}

echo "--- perfetto 58.2 consumer verification ---"
echo "bin dir: $BIN"

# C1 核心 CLI 齐全且可执行
for t in trace_processor_shell perfetto traced traced_probes tracebox traceconv; do
  check "C1 executable present: $t" test -x "$BIN/$t"
done

# C2 版本可打印
rc=0
out="$("$BIN/trace_processor_shell" --version 2>&1)" || rc=$?
check "C2 trace_processor_shell --version rc=0" test "$rc" -eq 0
matches "C2 reports Perfetto v58.2" 'Perfetto v58\.2' "$out"
echo "   version: $(printf '%s\n' "$out" | head -1)"

# C3 SQL 引擎可用（空 trace 上跑一条查询，验证 trace_processor 端到端可用）
tmp="./empty.pftrace"
: > "$tmp"
rc=0
sql="$("$BIN/trace_processor_shell" --query-string "select 1 as x" "$tmp" 2>&1)" || rc=$?
check "C3 query rc=0" test "$rc" -eq 0
matches "C3 SQL returns 1" '^1$' "$sql"
rm -f "$tmp"

# C4 CLI 用法可打印（纯参数解析路径，不启动服务）
# 注：perfetto 的 CmdLine 在打印 usage 后按设计返回 1，故断言「输出含 Usage」而非 rc=0。
for t in perfetto tracebox traceconv traced; do
  u="$("$BIN/$t" --help 2>&1 | head -5 || true)"
  matches_i "C4 $t --help prints usage" 'usage' "$u"
done

echo "test_consumer perfetto 58.2: $((checks - fails))/$checks checks PASS"
[ "$fails" -eq 0 ] || exit 1
exit 0
