#!/bin/sh
# test_package/consumer-e2e.sh — pnc 0.9.5 鸿蒙真机端到端消费用例
#
# 场景：一份「通讯录导出原文」（法/英/德混合自由文本 + 无效噪声）→ 规范化联系人表。
# 全程只用安装后的 bin/pnc（不碰源码树、不依赖构建目录），流程五步串联：
#   1) find -c FR   从混合语言原文里抽取全部号码（本国格式 + 国际格式）
#   2) valid        逐号校验，并确认噪声号码被拒绝（退出码语义）
#   3) info         取归属国家码/号码类型/离线地理编码地点
#   4) format -f nat 生成法国本地书写格式
#   5) dialout -c US 生成从美国拨出的国际拨号串
# 产出 contacts.sheet.tsv，与 data/expected.sheet.tsv 逐字节比对。
#
# 这是「真正跑通功能/流程」的端到端消费用例（文件进 → 产物出），
# 不是孤立断言：判据是生成的联系人表本身。
#
# 退出码：任一步失败或产物与期望不符即返回 1（CI L1 依赖此退出码）。
set -eu
# 管道失败也要暴露（POSIX sh 未必支持 pipefail，故容错处理）
set -o pipefail 2>/dev/null || true

PNC="${PNC_BIN:?PNC_BIN 未设置（应由 test_package/conanfile.py 导出）}"
HERE=$(cd "$(dirname "$0")" && pwd)
DATA="$HERE/data"
# 默认写到 test_package 副本目录内（CI 下 test_package 被复制到可写的 build 目录）；
# 不落 /tmp（鸿蒙 PC 上 /tmp 只读）。
WORK="${E2E_WORKDIR:-$HERE/e2e-out}"

rm -rf "$WORK"
mkdir -p "$WORK"
export LC_ALL=C

fail=0

echo ""
echo "=== pnc 0.9.5 鸿蒙真机端到端消费用例 ==="
echo "[场景] 通讯录导出原文 → 规范化联系人表（只用安装后的产物）"
echo "[输入] $DATA/contacts.raw.txt"
echo "[产物] $WORK/contacts.sheet.tsv"
echo "[CLI]  $PNC"

# ── 步骤 1：find，从混合语言原文抽取号码 ──────────────────────────
echo ""
echo "[1/5] find -c FR：抽取号码（通讯录默认国 FR）"
"$PNC" find -c FR "$(cat "$DATA/contacts.raw.txt")" | sort -u > "$WORK/all.e164"
n_found=$(wc -l < "$WORK/all.e164" | tr -d ' ')
echo "  抽出 $n_found 个号码："
sed 's/^/    /' "$WORK/all.e164"
if [ "$n_found" -lt 5 ]; then
	echo "  [FAIL] 抽取到的号码少于 5 个（期望 5 个：FR×2 / US / DE / GB）"
	exit 1
fi

# ── 步骤 2：valid，逐号校验 + 噪声拒绝语义 ────────────────────────
echo ""
echo "[2/5] valid：逐个校验，并确认无效噪声被拒绝"
while IFS= read -r num; do
	if "$PNC" valid "$num" >/dev/null 2>&1; then
		echo "  [ok]   $num 有效（退出码 0）"
	else
		echo "  [FAIL] $num 判无效"
		fail=1
	fi
done < "$WORK/all.e164"

set +e
"$PNC" valid "poste 1234" >/dev/null 2>&1
rc_junk=$?
set -e
if [ "$rc_junk" -ne 0 ]; then
	echo "  [ok]   噪声 'poste 1234' 被拒绝（退出码 $rc_junk）"
else
	echo "  [FAIL] 噪声 'poste 1234' 被误判为有效号码"
	fail=1
fi

# ── 步骤 3~5：info / format / dialout 生成联系人表 ────────────────
echo ""
echo "[3/5] info：归属国家码 / 号码类型 / 离线地理编码地点"
echo "[4/5] format -f nat：法国本地书写格式"
echo "[5/5] dialout -c US：从美国拨出的国际拨号串"
{
	printf 'e164\tcc\ttype\tlocation\tnat_fr\tdial_from_us\n'
	while IFS= read -r num; do
		info=$("$PNC" info "$num")
		cc=$(printf '%s\n' "$info" | sed -n 's/^country code: [0-9]* (\([A-Z][A-Z]\))$/\1/p')
		typ=$(printf '%s\n' "$info" | sed -n 's/^number type: //p')
		loc=$(printf '%s\n' "$info" | sed -n 's/^location: //p')
		nat=$("$PNC" format -f nat "$num")
		dial=$("$PNC" dialout -c US "$num")
		printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
			"$num" "$cc" "$typ" "$loc" "$nat" "$dial"
	done < "$WORK/all.e164"
} > "$WORK/contacts.sheet.tsv"

# 注意：本机 sh 对 `$(( $(...) - 1 ))` 这类嵌套替换会错拼命令，先取值再算
sheet_lines=$(wc -l < "$WORK/contacts.sheet.tsv")
sheet_lines=$(printf '%s' "$sheet_lines" | tr -d ' ')
n_rows=$((sheet_lines - 1))
echo "  生成联系人表 $n_rows 行："
sed 's/^/    /' "$WORK/contacts.sheet.tsv"

# ── 产物比对：生成物 vs 期望产物 ──────────────────────────────────
echo ""
echo "[校验] 产物比对：data/expected.sheet.tsv ↔ $WORK/contacts.sheet.tsv"
if diff -u "$DATA/expected.sheet.tsv" "$WORK/contacts.sheet.tsv" > "$WORK/diff.txt" 2>&1; then
	echo "  [ok]   端到端产物与期望逐行一致（$n_rows 行）"
else
	echo "  [FAIL] 端到端产物与期望不符："
	sed 's/^/    /' "$WORK/diff.txt"
	fail=1
fi

# ── 汇总 ─────────────────────────────────────────────────────────
echo ""
if [ "$fail" -ne 0 ]; then
	echo "=== 端到端消费用例: FAILED ==="
	exit 1
fi
echo "=== 端到端消费用例: PASSED（1 个用例，五步串联：find→valid→info→format→dialout）==="
exit 0
