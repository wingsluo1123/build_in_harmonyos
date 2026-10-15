#!/bin/sh
# Consumer test for the packaged pftools 3.2.12 executables.
#
# 覆盖三部分产物：
#   1. pftoolsV3 C 程序 (pfsearchV3 / pfscanV3) —— 真实 profile 搜索，检查命中
#   2. pftools release 2.3 Fortran 程序 (gtop) —— 由 flang-ohos 构建
#   3. Perl 脚本 (ps_scan.pl) —— 运行期依赖 File::Slurp (conanrun 注入 PERL5LIB)
set -eu

BIN="$1"
DATA="$2"
WORK="${TMPDIR:-/tmp}/pftools-test-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

echo "# --- 1. pftoolsV3: pfsearchV3 (SH3 profile vs SH3 sequences) ---"
"$BIN/pfsearchV3" -f "$DATA/sh2.prf" "$DATA/sh3.seq" > "$WORK/pfsearchV3.out"
HITS=$(grep -c "pos\." "$WORK/pfsearchV3.out" || true)
echo "# pfsearchV3 hits = $HITS"
[ "$HITS" -ge 1 ] || { echo "FAIL: pfsearchV3 produced no hits"; cat "$WORK/pfsearchV3.out"; exit 1; }

echo "# --- 2. pftoolsV3: pfscanV3 (PS50002 profile) ---"
"$BIN/pfscanV3" -f "$DATA/sh3.prf" "$DATA/sh3.seq" > "$WORK/pfscanV3.out" 2>&1
grep -q "PS50002" "$WORK/pfscanV3.out" || { echo "FAIL: pfscanV3 output unexpected"; cat "$WORK/pfscanV3.out"; exit 1; }

echo "# --- 3. Fortran release 2.3 component: gtop ---"
"$BIN/gtop" > "$WORK/gtop.out" 2>&1 || true
grep -q "gtop" "$WORK/gtop.out" || { echo "FAIL: gtop did not run"; cat "$WORK/gtop.out"; exit 1; }

echo "# --- 4. Perl helper: ps_scan.pl syntax/fload (File::Slurp) ---"
perl -c "$BIN/ps_scan.pl" > "$WORK/ps_scan.out" 2>&1
grep -q "syntax OK" "$WORK/ps_scan.out" || { echo "FAIL: ps_scan.pl not usable"; cat "$WORK/ps_scan.out"; exit 1; }

echo "# --- 5. [鸿蒙特有] /tmp 只读下 psa2msa 的 \$TMPDIR SCRATCH 回退 ---"
# 上游 psa2msa 用 Open(Status='SCRATCH')（落到 /tmp）；HarmonyOS 的 /tmp 是只读文件系统，
# 适配后改为 $TMPDIR 下的具名工作文件（patches/0011-src-Fortran-psa2msa.f.patch）。
# 本用例断言该回退在鸿蒙上真实生效：未适配的上游版本在此必然报
# "Error: Unable to create temporary file." 并返回非零。
SCRATCH="${TMPDIR:-/tmp}/pftools_psa2msa.scr"
rm -f "$SCRATCH"
"$BIN/pfsearchV3" -n -f -o 4 "$DATA/sh3.prf" "$DATA/sh3.seq" \
  | "$BIN/psa2msa" -du > "$WORK/psa2msa.msa"
grep -q "^>" "$WORK/psa2msa.msa" \
  || { echo "FAIL: psa2msa produced no MSA"; head -5 "$WORK/psa2msa.msa"; exit 1; }
[ -f "$SCRATCH" ] \
  || { echo "FAIL: psa2msa did not use the \$TMPDIR scratch file (上游 SCRATCH//tmp 回退失效)"; exit 1; }
echo "# psa2msa MSA records = $(grep -c '^>' "$WORK/psa2msa.msa"), scratch file = $SCRATCH"

echo "# all pftools consumer checks passed"
