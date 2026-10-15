#!/data/service/hnp/bin/bash
# test_package/test_megadepth.sh — megadepth 消费者视角功能测试
#
# 用法: test_megadepth.sh <megadepth 可执行文件绝对路径> <workdir>
#
# 输入 fixture 与期望输出全部取自上游仓库 tests/（MIT）：
#   fixtures/test.sam                                            (tests/test.sam)
#   fixtures/test_exons.bed                                      (tests/test_exons.bed)
#   fixtures/expected.annotation.per-base.exon_sums.tsv          (tests/test.bam.mosdepth.annotation.per-base.exon_sums.tsv)
#   fixtures/expected.unique.per-base.exon_sums.tsv              (tests/test.bam.mosdepth.unique.per-base.exon_sums.tsv)
#   fixtures/expected.alts.tsv                                   (tests/test.bam.orig.alts.tsv)
#
# ⚠️ fixture 一律使用**纯文本**：平台的 PR diff 端点对二进制文件不携带
# GIT binary patch 数据，checkout-pr 阶段 `git apply` 会因 "missing binary
# patch data" 直接失败（已实际踩中）。megadepth 的 get_file_format_extension()
# 把 .sam 归入 BAM 族、sam_open() 自动识别 SAM，故 test.sam 与 .bam 等价可用。
#
# 参数组合与上游 tests/test.sh 的 static 分支首个用例一致（test.sam 已含
# chr 前缀，故不需要 --add-chr-prefix human），产出的
# <prefix>.annotation.tsv / <prefix>.unique.tsv / <prefix>.alts.tsv
# 与上游期望文件逐行一致（真实数值断言，非存在性检查）。
set -u

MEGADEPTH="$1"
WORKDIR="$2"

HERE="$(cd "$(dirname "$0")" && pwd)"
FIX="$HERE/fixtures"

if [ ! -x "$MEGADEPTH" ]; then
    echo "[test] FAIL: megadepth 可执行文件不存在或不可执行: $MEGADEPTH" >&2
    exit 1
fi

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

PASS=0
FAIL=0

check() {
    desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  [PASS] $desc"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "[test] 1) --version / --help 冒烟"
out="$("$MEGADEPTH" --version 2>&1)"
case "$out" in
    *"megadepth 1.2.0"*)
        echo "  [PASS] --version 输出 'megadepth 1.2.0' (实际: $out)"
        PASS=$((PASS + 1))
        ;;
    *)
        echo "  [FAIL] --version 期望 'megadepth 1.2.0'，实际: $out"
        FAIL=$((FAIL + 1))
        ;;
esac
check "--help 退出码为 0" "$MEGADEPTH" --help

echo "[test] 2) 比对输入覆盖度/注释计算 (与上游 tests/test.sh static 分支同参数)"
"$MEGADEPTH" "$FIX/test.sam" \
    --prefix out --threads 4 --bigwig --auc --min-unique-qual 10 \
    --annotation "$FIX/test_exons.bed" --frag-dist --alts \
    --include-softclip --only-polya --read-ends --test-polya \
    --no-annotation-stdout --no-auc-stdout \
    --filter-out 260 > run.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "  [FAIL] megadepth 主计算退出码 $rc；日志尾部:" >&2
    tail -20 run.log >&2
    FAIL=$((FAIL + 1))
else
    echo "  [PASS] megadepth 主计算退出码 0"
    PASS=$((PASS + 1))
fi

echo "[test] 3) 产物与上游期望输出逐行比对"
check "<prefix>.annotation.tsv == 上游 expected.annotation.per-base.exon_sums.tsv" \
    diff out.annotation.tsv "$FIX/expected.annotation.per-base.exon_sums.tsv"
check "<prefix>.unique.tsv == 上游 expected.unique.per-base.exon_sums.tsv" \
    diff out.unique.tsv "$FIX/expected.unique.per-base.exon_sums.tsv"

echo "[test] 4) 附加产物与二次计算路径"
check "--bigwig 产出 out.all.bw" test -s out.all.bw
check "--frag-dist 产出 out.fraglen.tsv/out.fragdist.tsv" \
    bash -c 'ls out.frag* > /dev/null 2>&1'
"$MEGADEPTH" "$FIX/test.sam" --annotation "$FIX/test_exons.bed" \
    --op mean > mean.tsv 2> mean.err
rc=$?
if [ "$rc" -eq 0 ] && [ -s mean.tsv ]; then
    echo "  [PASS] --op mean 输出非空 ($(wc -l < mean.tsv) 行)"
    PASS=$((PASS + 1))
else
    echo "  [FAIL] --op mean 退出码 $rc；stderr 尾部:" >&2
    tail -10 mean.err >&2
    FAIL=$((FAIL + 1))
fi

echo "[test] 5) 输入格式错误路径必须非零退出"
check "未知扩展名输入返回非零" bash -c "! \"$MEGADEPTH\" fixtures.unknown > /dev/null 2>&1"

echo
echo "[test] 结果: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    echo "[test] FAILED" >&2
    exit 1
fi
echo "[test] ALL PASSED"
exit 0
