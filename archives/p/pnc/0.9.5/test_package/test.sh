#!/bin/sh
# test_package/test.sh — pnc 消费端验证（只用安装后的 bin/pnc）
#
# 断言与上游 tests.sh 对齐（valid 判定与退出码、format 的 e164/nat/int、
# find 从自然语言里抽取号码），另加 help 与 info（离线地理编码）。
# 退出码：任一断言失败即返回 1（CI L1 依赖此退出码）。
set -eu
# 管道失败也要暴露（POSIX sh 未必支持 pipefail，故容错处理）
set -o pipefail 2>/dev/null || true

PNC="${PNC_BIN:?PNC_BIN 未设置（应由 test_package/conanfile.py 导出）}"

pass=0
fail=0

report() { # report <描述> <期望> <实际>
	if [ "$2" = "$3" ]; then
		pass=$((pass + 1))
		echo "  [ok]   $1"
	else
		fail=$((fail + 1))
		echo "  [FAIL] $1 — 期望 '$2'，实际 '$3'"
	fi
}

# pnc 的 help 输出把 VERSION 等标签加了 ANSI 加粗（\033[1mVERSION\033[0m），
# 逐字匹配前先去掉转义序列。
ESC=$(printf '\033')
strip_ansi() { sed "s/${ESC}\[[0-9;]*m//g"; }

echo ""
echo "=== pnc 0.9.5 test_package ==="
echo "[info] CLI: $PNC"

# ── A. 子命令输出 ────────────────────────────────────────────────
echo "[A] bin/pnc 子命令"

out=$("$PNC" help 2>&1 | strip_ansi)
case "$out" in
*"VERSION: 0.9.5"*) report "help 报告版本 0.9.5" "yes" "yes" ;;
*) report "help 报告版本 0.9.5" "yes" "no" ;;
esac
case "$out" in
*"DESCRIPTION: phone numbers"*) report "help 报告 DESCRIPTION" "yes" "yes" ;;
*) report "help 报告 DESCRIPTION" "yes" "no" ;;
esac

report "format -c FR 0123456789 → e164" \
	"+33123456789" "$("$PNC" format -c FR "0123456789")"
report "format -c FR -f nat 0123456789" \
	"01 23 45 67 89" "$("$PNC" format -c FR -f nat "0123456789")"
report "format -f int +12025550110" \
	"+1 202-555-0110" "$("$PNC" format -f int "+12025550110")"
report "find -c FR 抽取文本中的号码" \
	"+33123456789" "$("$PNC" find -c FR "rappelle-moi au 01 23 4 56789")"
report "dialout -c FR +12025550110" \
	"00 1 202-555-0110" "$("$PNC" dialout -c FR "+12025550110")"

# ── A2. 退出码（valid 的结果语义） ────────────────────────────────
echo "[A2] 退出码"

set +e
"$PNC" valid "+33123456789" >/dev/null 2>&1
rc=$?
set -e
report "valid +33123456789 退出码 0" "0" "$rc"

set +e
"$PNC" valid "(202) 555-0110" >/dev/null 2>&1
rc=$?
set -e
report "valid '(202) 555-0110' 判无效（非 0 退出）" "non-zero" \
	"$([ "$rc" -ne 0 ] && echo non-zero || echo 0)"

set +e
"$PNC" valid -c US "(202) 555-0110" >/dev/null 2>&1
rc=$?
set -e
report "valid -c US '(202) 555-0110' 退出码 0" "0" "$rc"

# ── A3. info 输出（离线地理编码） ─────────────────────────────────
echo "[A3] info（离线地理编码）"

info=$("$PNC" info -c FR "0123456789")
case "$info" in
*"location: France"*) report "info -c FR location=France" "yes" "yes" ;;
*) report "info -c FR location=France" "yes" "no" ;;
esac
case "$info" in
*"country code: 33 (FR)"*) report "info 国家码 33 (FR)" "yes" "yes" ;;
*) report "info 国家码 33 (FR)" "yes" "no" ;;
esac

# ── 汇总 ─────────────────────────────────────────────────────────
echo ""
echo "=== 结果: ${pass} passed, ${fail} failed ==="
if [ "$fail" -ne 0 ]; then
	echo "FAILED"
	exit 1
fi
echo "ALL PASSED"
exit 0
