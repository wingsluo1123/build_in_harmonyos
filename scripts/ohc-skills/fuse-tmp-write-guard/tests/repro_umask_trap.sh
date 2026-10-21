#!/bin/sh
# repro_umask_trap.sh — FUSE umask 陷阱复现 + SKILL 生效双向验证
# （fuse-tmp-write-guard SKILL Step4 复现脚本；样例库: oddjob 0.34.7）
#
# Phase A（SKILL 关闭）: 按 autotools config.status 的确切行为复现——
#   umask 077 + mktemp -d "./confXXXXXX" + 写 subs1.awk。
#   在受影响环境（本仓库 FUSE 工作区）预期 Permission denied（原始报错）。
# Phase B（SKILL 开启）: 同一操作经 scripts/ohc_umask_wrap.sh（umask 000
#   注入）执行，预期成功。
#
# 样例库对应关系（oddjob 0.34.7，两处实证之一）:
#   * Phase A 的探针操作 = config.status 第 860 行段落的逐字复刻
#     （mktemp -d ./confXXXXXX → 写 subs1.awk → Permission denied）；
#   * 证据行样例见 knowledge 条目与 skills/fuse-tmp-write-guard/SKILL.md。
#
# 判定:
#   A 被拒 + B 成功           → TRAP_CONFIRMED_SKILL_EFFECTIVE（exit 0）
#   A 可写（正常 FS 环境）     → ENV_NOT_AFFECTED，SKILL 不适用（exit 0）
#   其他（A 异常/B 意外失败）   → UNEXPECTED（exit 1）
#
# 约束遵循: 全程日志重定向到文件，无管道下游（防 SIGPIPE）；不写死机器
# 本地绝对路径（工作目录取 $1 或 ${TMPDIR:-$HOME/tmp} 推导）。
#
# 用法: repro_umask_trap.sh [workdir]

WORKDIR=${1:-"${TMPDIR:-$HOME/tmp}/fuse-umask-repro"}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WRAP="$SCRIPT_DIR/../scripts/ohc_umask_wrap.sh"

[ -x "$WRAP" ] || WRAP="$SCRIPT_DIR/../scripts/ohc_umask_wrap.sh"
[ -f "$WRAP" ] || { echo "FATAL: wrapper not found: $WRAP" >&2; exit 2; }

mkdir -p "$WORKDIR" || exit 2
cd "$WORKDIR" || exit 2

LOG_A="$WORKDIR/phaseA.log"
LOG_B="$WORKDIR/phaseB.log"
RES_A="$WORKDIR/phaseA.result"
rm -f "$LOG_A" "$LOG_B" "$RES_A"

# ---------- Phase A: SKILL 关闭（复现 config.status 原始报错） ----------
rm -rf ./confA* 2>/dev/null
(
  umask 077
  d=$(mktemp -d "./confXXXXXX") || { echo "mktemp_failed" >&2; exit 97; }
  if echo probe > "$d/subs1.awk" 2>>"$LOG_A"; then
      echo "PHASEA_WRITE_OK" > "$RES_A"
  else
      echo "PHASEA_WRITE_DENIED" > "$RES_A"
      echo "config.status[repro]: can't create $d/subs1.awk: Permission denied" >> "$LOG_A"
  fi
  rm -rf "$d"
  exit 0
)
A_RESULT=$(cat "$RES_A" 2>/dev/null || echo "UNKNOWN")
echo "Phase A (skill off): $A_RESULT"
[ -s "$LOG_A" ] && { echo "--- phaseA.log ---"; cat "$LOG_A"; }

# ---------- Phase B: SKILL 开启（umask 000 注入 wrapper） ----------
rm -rf ./confB* 2>/dev/null
cat > "$WORKDIR/inner.sh" <<'EOF'
d=$(mktemp -d "./confXXXXXX") || exit 97
echo probe > "$d/subs1.awk" || exit 98
rm -rf "$d"
exit 0
EOF

"$WRAP" sh "$WORKDIR/inner.sh" > "$LOG_B" 2>&1
B_RC=$?
echo "Phase B (skill on, umask000 injected): rc=$B_RC"
[ -s "$LOG_B" ] && { echo "--- phaseB.log ---"; cat "$LOG_B"; }

rm -f "$RES_A" "$WORKDIR/inner.sh"

# ---------- 判定 ----------
if [ "$A_RESULT" = "PHASEA_WRITE_OK" ]; then
    echo "RESULT: ENV_NOT_AFFECTED — umask077 目录可写，本环境无该陷阱，SKILL 不适用（正常）"
    exit 0
fi
if [ "$A_RESULT" = "PHASEA_WRITE_DENIED" ] && [ "$B_RC" -eq 0 ]; then
    echo "RESULT: TRAP_CONFIRMED_SKILL_EFFECTIVE — A 复现原始报错被拒，B 经 wrapper 写入成功"
    exit 0
fi
echo "RESULT: UNEXPECTED — A=$A_RESULT B_RC=$B_RC（检查 phaseA/phaseB.log）"
exit 1
