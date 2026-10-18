#!/data/service/hnp/bin/bash
# test_package/test_pizzly.sh —— pizzly 消费者端到端验证（鸿蒙 PC 目标机实跑）
#
# 被测对象：本次 `conan create` 安装后的 `bin/pizzly`。脚本由 test_package/conanfile.py
# 以 env="conanrun" 拉起，PATH 指向 Conan cache 中**已安装的 package_folder/bin**，
# 不使用源码构建目录产物，也不使用任何系统同名程序（OHOS 上不存在 pizzly）。
#
# 用例：
#   E2E-PIZZLY-001  融合基因检出主流程（真实 kallisto --fusion 输入 → 融合调用结果）
#   E2E-PIZZLY-002  GTF 注释缓存的生成与复用（二次运行命中缓存，结果一致）
#
# fixtures/ 内容与来源（逐字节 sha256 见 MANIFEST.yml）：
#   fusion.txt            kallisto 0.52.0 `quant --fusion` 对上游 test/reads_*.fastq.gz 的
#                         真实输出（上游 test/Snakefile 的 rule kallisto_quant 同参数）
#   transcripts.gtf.gz    上游 test/ 自带参考注释（Ensembl 85 子集，原样）
#   transcripts.fasta.gz  上游 test/ 自带参考转录组（原样）
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="$HERE/fixtures"
WORK="$PWD/pizzly-e2e-work"
rm -rf "$WORK"
mkdir -p "$WORK/case1" "$WORK/case2" "$WORK/data"

cleanup() {
    status=$?
    if [ "$status" -eq 0 ]; then
        rm -rf "$WORK"
    else
        echo "pizzly E2E failed (exit $status); preserving logs under $WORK" >&2
        find "$WORK" -maxdepth 2 -type f -print >&2 || true
    fi
}
trap cleanup EXIT

command -v python3 >/dev/null 2>&1 || {
    echo "FAIL: python3 is required to verify pizzly JSON output" >&2
    exit 1
}
command -v base64 >/dev/null 2>&1 || {
    echo "FAIL: base64 is required to decode the gzipped reference fixtures" >&2
    exit 1
}

# 参考 GTF/FASTA 是 gzip 压缩数据，按仓库约定以 .b64 承载（test_package 不走 preflight PF2
# 对裸归档扩展名的制品闸，先例：archives/b/blur、archives/b/bozohttpd 的 test_package/*.b64）。
# 这里在运行时解码，并逐字节校验解码结果，确保测试输入与上游 test/ 原件完全一致。
decode_fixture() {
    src="$1"
    dst="$2"
    want="$3"
    base64 -d "$src" > "$dst"
    got="$(sha256sum "$dst" | awk '{print $1}')"
    if [ "$got" != "$want" ]; then
        echo "FAIL: $dst sha256 mismatch: got $got, want $want" >&2
        exit 1
    fi
    echo "[fixture] $(basename "$dst") decoded, sha256=$got"
}
decode_fixture "$FIXTURES/transcripts.gtf.gz.b64" "$WORK/data/transcripts.gtf.gz" \
    9a2cf33ec78412f4cc7c087b4be88bb6596b9c76658e5e952092eb90673246ab
decode_fixture "$FIXTURES/transcripts.fasta.gz.b64" "$WORK/data/transcripts.fasta.gz" \
    bcf11e8d281971dd7b3a1cc6892cd399863fdf43e05c76b1a58f328327d0c281

if ! BIN="$(command -v pizzly)"; then
    echo "FAIL: pizzly 不在 PATH 上（conanrun env 未暴露安装后的 bin/pizzly）" >&2
    echo "      PATH=$PATH" >&2
    exit 1
fi
echo "[env] pizzly -> $BIN"
ls -l "$BIN"

echo
echo "=== smoke: pizzly --version (不单独计为 E2E 用例) ==="
pizzly --version 2>&1 | tee "$WORK/version.txt"
grep -q "pizzly version: 0.37.3" "$WORK/version.txt"

# ─────────────────────────────────────────────────────────────────────────────
# E2E-PIZZLY-001：融合基因检出主流程
#   输入：真实 kallisto --fusion 输出 fusion.txt + 参考 GTF + 参考 FASTA
#   流程：kallisto 候选融合 → 假阳性过滤 → 断点级转录本组装 → 融合丰度定量
#   预期业务输出：保留 308/366 条候选记录，产出 9 对融合基因（含 EML4-ALK）、
#                 146 条融合转录本，且 output.fusions.fasta 与 .json 一一对应
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "=== E2E-PIZZLY-001: fusion calling ==="
cd "$WORK/case1"
pizzly -k 31 \
    --gtf "$WORK/data/transcripts.gtf.gz" \
    --cache "$WORK/case1/cache.txt" \
    --align-score 2 \
    --insert-size 400 \
    --fasta "$WORK/data/transcripts.fasta.gz" \
    --output "$WORK/case1/output" \
    "$FIXTURES/fusion.txt" 2>&1 | tee "$WORK/case1/run.log"

grep -q "GTF file contains 36 genes and 289 transcripts" "$WORK/case1/run.log"
grep -q "Number of kept records 308 out of 366" "$WORK/case1/run.log"
test -s "$WORK/case1/output.json"
test -s "$WORK/case1/output.fusions.fasta"

python3 - "$WORK/case1/output.json" "$WORK/case1/output.fusions.fasta" <<'PY'
import json
import sys

json_path, fasta_path = sys.argv[1], sys.argv[2]
data = json.load(open(json_path, encoding="utf-8"))
assert list(data.keys()) == ["genes"], f"unexpected top-level keys: {list(data.keys())}"
genes = data["genes"]
assert len(genes) == 9, f"expected 9 fusion gene pairs, got {len(genes)}"

pairs = {(g["geneA"]["name"], g["geneB"]["name"]): g for g in genes}
assert ("EML4", "ALK") in pairs, f"EML4-ALK fusion missing; pairs={sorted(pairs)}"
eml4_alk = pairs[("EML4", "ALK")]
assert eml4_alk["geneA"]["id"] == "ENSG00000143924.18"
assert eml4_alk["geneB"]["id"] == "ENSG00000171094.15"
assert eml4_alk["paircount"] == 4, eml4_alk["paircount"]
assert len(eml4_alk["transcripts"]) == 9, len(eml4_alk["transcripts"])

# 每个 gene 记录的 transcript 条目数与 readpairs 必须自洽
for g in genes:
    assert g["paircount"] + g["splitcount"] == len(g["readpairs"]), g["geneA"]["name"]
    for t in g["transcripts"]:
        assert t["fasta_record"], "empty fasta_record"
        assert t["support"] >= 1
        for read in t["reads"]:
            assert 0 <= read < len(g["readpairs"]), "read index out of range"

total_transcripts = sum(len(g["transcripts"]) for g in genes)
assert total_transcripts == 146, f"expected 146 assembled fusions, got {total_transcripts}"

headers = [line[1:].strip() for line in
           open(fasta_path, encoding="utf-8") if line.startswith(">")]
assert len(headers) == 146, f"expected 146 fasta records, got {len(headers)}"

json_records = {t["fasta_record"] for g in genes for t in g["transcripts"]}
assert json_records == set(headers), "output.json and output.fusions.fasta disagree"

# 抽一条融合记录核对序列本身：fasta 长度须等于记录声明的区间长度之和
seqs, name = {}, None
for line in open(fasta_path, encoding="utf-8"):
    if line.startswith(">"):
        name = line[1:].strip()
        seqs[name] = ""
    else:
        seqs[name] += line.strip()
rec = eml4_alk["transcripts"][0]
span = ((rec["transcriptA"]["endPos"] - rec["transcriptA"]["startPos"]) +
        (rec["transcriptB"]["endPos"] - rec["transcriptB"]["startPos"]))
assert len(seqs[rec["fasta_record"]]) == span, (
    f"{rec['fasta_record']}: fasta length {len(seqs[rec['fasta_record']])} != declared span {span}")

print("E2E-PIZZLY-001: PASS — 9 fusion gene pairs, 146 assembled fusion transcripts, "
      "EML4-ALK paircount=4, json/fasta consistent")
PY

# ─────────────────────────────────────────────────────────────────────────────
# E2E-PIZZLY-002：GTF 注释缓存生成与复用
#   首次运行创建 cache.txt；二次运行必须走缓存分支（loadTranscriptome）并给出
#   与首次完全一致的融合调用结果。
# ─────────────────────────────────────────────────────────────────────────────
echo
echo "=== E2E-PIZZLY-002: GTF cache generation and reuse ==="
test -s "$WORK/case1/cache.txt"
cd "$WORK/case2"
pizzly -k 31 \
    --gtf "$WORK/data/transcripts.gtf.gz" \
    --cache "$WORK/case1/cache.txt" \
    --align-score 2 \
    --insert-size 400 \
    --fasta "$WORK/data/transcripts.fasta.gz" \
    --output "$WORK/case2/output" \
    "$FIXTURES/fusion.txt" 2>&1 | tee "$WORK/case2/run.log"

grep -q "Opening cached file" "$WORK/case2/run.log"
grep -q "loaded 36 genes and 289 transcripts" "$WORK/case2/run.log"
grep -q "Number of kept records 308 out of 366" "$WORK/case2/run.log"

sha256sum "$WORK/case1/output.json" | awk '{print $1}' > "$WORK/case1.json.sha256"
sha256sum "$WORK/case2/output.json" | awk '{print $1}' > "$WORK/case2.json.sha256"
diff -u "$WORK/case1.json.sha256" "$WORK/case2.json.sha256"
diff -u "$WORK/case1/output.fusions.fasta" "$WORK/case2/output.fusions.fasta"

echo "E2E-PIZZLY-002: PASS — cache reused (36 genes / 289 transcripts), output identical to cold run"

echo
echo "pizzly consumer E2E: PASS (E2E-PIZZLY-001, E2E-PIZZLY-002)"
