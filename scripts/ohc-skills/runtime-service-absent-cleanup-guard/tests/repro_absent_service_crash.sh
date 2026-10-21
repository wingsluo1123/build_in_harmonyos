#!/bin/sh
# repro_absent_service_crash.sh — 「运行期服务缺失 → 清理路径崩溃」A/B 复现脚本.
#
# 用法:
#   tests/repro_absent_service_crash.sh [输出目录]
#
# 环境变量（均有默认值，无任何本地绝对路径硬编码）:
#   CC           编译器，默认 clang（可用 conan profile 注入的绝对路径覆盖）
#   SKILL_DIR    本 SKILL 根目录，默认脚本所在目录的上一级
#   SIGN_TOOL    OHOS ELF 签名工具，默认 binary-sign-tool（PATH 内查找；缺失则跳过）
#
# 产物：$OUT/stage-a.log（无守卫，应崩溃）、$OUT/stage-b.log（有守卫，应优雅退出）
# 判定行（CI 可 grep）:
#   ABSENT_SERVICE_CRASH_REPRODUCED=yes
#   GUARD_CONFIRMED=yes
#   DETECTOR_HIT=yes
#   REPRO_SCRIPT_EFFECTIVE=yes
#
# 注意：所有被测进程输出一律重定向到文件，绝不接管道 —— 被测进程若读到
# SIGPIPE 会提前死掉，A/B 结论就失真了。
set -u

SKILL_DIR=${SKILL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}
OUT=${1:-${TMPDIR:-/tmp}/absent-service-repro}
CC=${CC:-clang}
PYTHON=${PYTHON:-python3}
SIGN_TOOL=${SIGN_TOOL:-binary-sign-tool}

mkdir -p "$OUT" || exit 4
SRC="$SKILL_DIR/samples/graceful_cleanup_demo.c"

fail() {
  echo "REPRO_SCRIPT_EFFECTIVE=no"
  echo "REASON=$*"
  exit 1
}

[ -f "$SRC" ] || fail "sample source missing: $SRC"

# 编译并在必要时补签名（OHOS 上直接执行未签名 ELF 会 EPERM）
build_and_run() {
  _tag=$1
  _guard=$2
  _bin="$OUT/$_tag"
  "$CC" -DGUARD="$_guard" -O0 -g -o "$_bin" "$SRC" \
    > "$OUT/$_tag.build.log" 2>&1 || fail "compile failed for $_tag (see $OUT/$_tag.build.log)"
  chmod 755 "$_bin" 2>/dev/null
  "$_bin" > "$OUT/$_tag.log" 2>&1
  _rc=$?
  if [ "$_rc" -eq 126 ] && command -v "$SIGN_TOOL" >/dev/null 2>&1; then
    "$SIGN_TOOL" sign -inFile "$_bin" -outFile "$_bin.signed" -selfSign 1 \
      > "$OUT/$_tag.sign.log" 2>&1 || fail "signing failed for $_tag"
    chmod 755 "$_bin.signed" 2>/dev/null
    "$_bin.signed" > "$OUT/$_tag.log" 2>&1
    _rc=$?
  fi
  echo "$_rc" > "$OUT/$_tag.rc"
  return 0
}

# ---- A 组：关闭策略（无守卫）→ 期望崩溃 ----
build_and_run stage-a 0
RC_A=$(cat "$OUT/stage-a.rc")
echo "STAGE_A_RC=$RC_A"
if [ "$RC_A" -eq 139 ] || [ "$RC_A" -eq 134 ]; then
  echo "ABSENT_SERVICE_CRASH_REPRODUCED=yes"
else
  fail "stage A did not crash as expected (rc=$RC_A; see $OUT/stage-a.log)"
fi

# ---- B 组：启用策略（加守卫）→ 期望优雅失败 ----
build_and_run stage-b 1
RC_B=$(cat "$OUT/stage-b.rc")
echo "STAGE_B_RC=$RC_B"
if [ "$RC_B" -eq 0 ] || [ "$RC_B" -eq 1 ]; then
  echo "GUARD_CONFIRMED=yes"
else
  fail "stage B did not fail gracefully (rc=$RC_B; see $OUT/stage-b.log)"
fi

# ---- 检测脚本自校验：L1 应命中上游未修补形态的 fixture ----
# 注意扫 fixtures 而不是 samples 根目录：样例源码用 #if GUARD 同时携带
# 「有守卫」与「无守卫」两条分支，会让 L1「是否已有守卫」的判定失真。
SCAN=$("$PYTHON" "$SKILL_DIR/scripts/detect_absent_service_crash.py" \
        scan --src "$SKILL_DIR/samples/fixtures" 2>&1)
echo "$SCAN" > "$OUT/scan.log"
echo "$SCAN" | grep -q "ABSENT_SERVICE_CLEANUP_CANDIDATE=yes" \
  && echo "DETECTOR_HIT=yes" \
  || fail "detector missed the sample (see $OUT/scan.log)"

# ---- 检测脚本自校验：L2 应把 A 组日志判为本类崩溃 ----
"$PYTHON" "$SKILL_DIR/scripts/detect_absent_service_crash.py" \
  runtime --log "$OUT/stage-a.log" --rc "$RC_A" > "$OUT/runtime.log" 2>&1
if grep -q "ABSENT_SERVICE_CRASH_CONFIRMED=yes" "$OUT/runtime.log"; then
  echo "DETECTOR_RUNTIME_CONFIRMED=yes"
else
  fail "runtime detector did not confirm stage A (see $OUT/runtime.log)"
fi

echo "REPRO_SCRIPT_EFFECTIVE=yes"
echo "ARTIFACTS=$OUT"
