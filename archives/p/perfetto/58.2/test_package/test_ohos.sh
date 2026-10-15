#!/usr/bin/env bash
# test_package/test_ohos.sh — 鸿蒙平台特有校验（与消费者用例分开计数，不重复计入）
#
# OHOS 平台特性：
#   T1 产物必须是 AArch64 ELF
#   T2 产物必须带 .codesign 段（OHOS 用户存储执行 ELF 的必要条件；strip 会使其失效）
#   T3 运行期 tmp 目录约定（/tmp 为只读 erofs，需依赖 TMPDIR）
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

# contains <name> <needle> <haystack> —— 固定子串匹配（haystack 为已捕获的输出，不参与 shell 求值）。
contains() {
  local name="$1" needle="$2" hay="${3:-}"
  case "$hay" in
    *"$needle"*) note_pass "$name" ;;
    *)           note_fail "$name" ;;
  esac
}

echo "--- perfetto 58.2 HarmonyOS-specific checks ---"

# T1 AArch64 ELF
for t in trace_processor_shell perfetto traced traced_probes tracebox traceconv; do
  hdr="$(readelf -h "$BIN/$t" 2>/dev/null || true)"
  contains "T1 aarch64 ELF: $t" "AArch64" "$hdr"
done

# T2 .codesign 段（OHOS 特有）
for t in trace_processor_shell perfetto traced; do
  secs="$(readelf -S "$BIN/$t" 2>/dev/null || true)"
  contains "T2 .codesign section: $t" ".codesign" "$secs"
done

# T3 只读 /tmp 下仍可运行（依赖 TMPDIR；缺 TMPDIR 时应给出可诊断失败而非静默通过）
tmpd="${TMPDIR:-/storage/Users/currentUser/.opendesk-tmp/tmp}"
mkdir -p "$tmpd" 2>/dev/null || true
check "T3 tmp dir is writable: $tmpd" test -w "$tmpd"
: > "$tmpd/.pftrace-probe" 2>/dev/null || true
check "T3 tmp dir accepts files" test -f "$tmpd/.pftrace-probe"
rm -f "$tmpd/.pftrace-probe"

echo "test_ohos perfetto 58.2: $((checks - fails))/$checks checks PASS"
[ "$fails" -eq 0 ] || exit 1
exit 0
