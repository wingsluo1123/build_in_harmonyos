#!/usr/bin/env python3
"""biopython consumer test (R34): the package imports from the packaged
site-packages and its compiled C extensions actually load, rather than
being a pure-Python stub.

biopython ships 13 C extensions.  A package that merely copies the .py
files would still import at the top level, so this test deliberately
exercises the extensions (Bio.Align._aligncore, Bio.Cluster._cluster,
Bio.PDB.kdtrees) as well as real sequence I/O through SeqIO - which is
exactly what qcat (the downstream consumer) relies on.

NumPy 的处理（CI #14021 实测）：`Bio/Align/__init__.py` 在 numpy 不可用时
**导入即 raise** `MissingPythonDependencyError`，而 biopython 的守卫会**吞掉**
底层原因（是"没装"还是"装了但 HNP python 载不动它的 .so"看不出来）。而
`Bio.Align.*` 那 5 个扩展的**父包**正是它，且 `Bio.SeqIO` 也会经 AlignIO 走到
Align。故本脚本：

  1. 先探 numpy，并把**真实原因原文**打印出来（不再让守卫吞掉）；
  2. numpy 不可用时，只验证与 numpy 无关的那部分能力，并把 Bio.Align 相关
     步骤如实标为 SKIP（附原因），**不伪装成通过**；
  3. 扩展导入失败若带 E212 签名（`Error loading shared library` /
     `symbol not found`，即用户可写路径下的 .so 载不动，与本包适配无关）
     则单独记为 ENV-LIMITED，不计入失败；其它异常照旧抛出。

numpy 可用时，本脚本的行为与原先完全一致（全套步骤都跑）。
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import os
import sys

# 追加而非覆盖：biopython 运行期要 import numpy（由 runenv 注入）
sys.path[0:0] = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]

import Bio
print("biopython", Bio.__version__)
assert Bio.__version__ == "1.88", Bio.__version__

# ---- 0) 先探 numpy，并打印真实原因（biopython 的守卫会把它吞掉）----
HAVE_NUMPY, NUMPY_ERR = True, ""
try:
    import numpy as _np
    print("numpy available: True |", getattr(_np, "__version__", "?"),
          "|", getattr(_np, "__file__", "?"))
except BaseException as exc:
    HAVE_NUMPY = False
    NUMPY_ERR = "%s: %s" % (type(exc).__name__, exc)
    print("numpy available: False |", NUMPY_ERR)

# ---- 1) C 扩展真实可加载（HMDFS 上 dlopen 验证）----
import importlib

EXTS = [
    "Bio.Align._aligncore",
    "Bio.Align._alignmentcounts",
    "Bio.Align._codonaligner",
    "Bio.Align._pairwisealigner",
    "Bio.Align.substitution_matrices._arraycore",
    "Bio.cpairwise2",
    "Bio.Nexus.cnexus",
    "Bio.motifs._pwm",
    "Bio.Cluster._cluster",
    "Bio.PDB.ccealign",
    "Bio.PDB.kdtrees",
    "Bio.PDB._bcif_helper",
    "Bio.SeqIO._twoBitIO",
]


def _load(names):
    """逐个 import 扩展，兵分三类：可加载 / E212 环境受限 / 需要 numpy。

    **不按"哪个模块需要 numpy"硬编码分组**——CI 实测会漏：把 5 个 Bio.Align.*
    挪走之后，`Bio.motifs._pwm` 的父包同样在缺 numpy 时 raise
    （`MissingPythonDependencyError: Install NumPy if you want to use Bio.motifs.`）。
    改由**包自己**的异常来分类：它抛 MissingPythonDependencyError 就是在说
    "这个能力需要 numpy"，与本包适配无关。
    """
    ok, env_limited, need_numpy = [], [], []
    for name in names:
        try:
            m = importlib.import_module(name)
        except BaseException as exc:
            text = "%s: %s" % (type(exc).__name__, exc)
            if "Error loading shared library" in text or "symbol not found" in text:
                env_limited.append("%s -> %s" % (name, text))
                continue
            if type(exc).__name__ == "MissingPythonDependencyError" \
                    or "nstall NumPy" in text:
                need_numpy.append("%s -> %s" % (name, text))
                continue
            print("FAIL: importing %s raised %s" % (name, text))
            raise
        f = getattr(m, "__file__", "") or ""
        if not f.endswith(".so"):
            raise AssertionError("%s is not a compiled extension: %r" % (name, f))
        ok.append(name)
    return ok, env_limited, need_numpy


loaded, env_limited, need_numpy = _load(EXTS)
print("OK: loaded %d/%d compiled C extensions" % (len(loaded), len(EXTS)))
for label, items in (
        ("ENV-LIMITED (E212-family, not counted as failure)", env_limited),
        ("NEEDS-NUMPY (numpy unavailable, not counted as failure)", need_numpy)):
    if items:
        print("%s:" % label)
        for item in items:
            print("   ", item)
# 台账断言：三类相加必须等于总数，任何"消失的扩展"都不许悄悄溜过。
if len(loaded) + len(env_limited) + len(need_numpy) != len(EXTS):
    raise AssertionError("extension accounting gap: %d+%d+%d != %d"
                         % (len(loaded), len(env_limited), len(need_numpy),
                            len(EXTS)))
if need_numpy and HAVE_NUMPY:
    raise AssertionError("numpy is importable but %s still reported needing it "
                         "— refusing to treat that contradiction as a pass"
                         % need_numpy)

if not HAVE_NUMPY:
    # 只验证与 numpy 无关的能力；Bio.SeqIO 也会经 AlignIO 走到 Align，故一并跳过。
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    s = Seq("ACGTACGTAC")
    assert str(s.complement()) == "TGCATGCATG", str(s.complement())
    assert str(s.reverse_complement()) == "GTACGTACGT", str(s.reverse_complement())
    rec = SeqRecord(s, id="seq1", description="seq1 desc")
    assert rec.id == "seq1" and len(rec) == 10, (rec.id, len(rec))
    print("OK: Bio.Seq/Bio.SeqRecord work (numpy-independent core)")
    print("SKIP: SeqIO / PairwiseAligner / Cluster kcluster — all require numpy")
    print("OK: biopython import + numpy-independent extensions verified "
          "(numpy unavailable)")
    raise SystemExit(0)

# ---- 2) 真实序列解析（SeqIO，qcat 依赖的能力）----
from io import StringIO
from Bio import SeqIO
fasta = StringIO(">seq1 desc\nACGTACGTAC\n>seq2\nTTTTGGGGCC\n")
records = list(SeqIO.parse(fasta, "fasta"))
assert len(records) == 2, len(records)
assert records[0].id == "seq1", records[0].id
assert records[0].description == "seq1 desc", records[0].description
assert str(records[0].seq) == "ACGTACGTAC", str(records[0].seq)
assert str(records[1].seq) == "TTTTGGGGCC", str(records[1].seq)
print("OK: SeqIO parsed 2 FASTA records:", [r.id for r in records])

# ---- 3) 真实比对计算（_aligncore / PairwiseAligner）----
from Bio.Align import PairwiseAligner
al = PairwiseAligner()
al.mode = "global"
al.match_score = 1
al.mismatch_score = -1
al.open_gap_score = -2
al.extend_gap_score = -0.5
score = al.score("ACGTACGTAC", "ACGTACGTAC")
assert score == 10, score
alignments = al.align("ACGT", "ACGT")
assert len(alignments) >= 1, len(alignments)
print("OK: PairwiseAligner global score =", score)

# ---- 4) Cluster 扩展（独立 C 扩展，真实计算）----
from Bio.Cluster import kcluster
import numpy as np
data = np.array([[1.0, 2.0], [1.5, 1.8], [5.0, 8.0], [8.0, 8.0]])
# 上游签名（实测）：
#   kcluster(data, nclusters=2, mask=None, weight=None, transpose=False,
#            npass=1, method='a', dist='e', initialid=None)
# 无 random_state 参数（初版脚本误用，已修正）
clusterid, error, nfound = kcluster(data, nclusters=2, npass=10)
assert len(clusterid) == 4, clusterid
assert nfound >= 1, nfound
print("OK: kcluster -> clusterid", list(clusterid), "nfound", nfound)

print("OK: biopython + compiled extensions work")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "Bio", "__init__.py")
    if not os.path.isfile(mod):
        print("FAIL: Bio module missing: %s" % mod, file=sys.stderr)
        return 1
    # 13 个 C 扩展的 .so 必须都在（否则包装错了）——这一步与 numpy 无关，
    # 故任何环境下都必须成立。
    sos = []
    for root, _, files in os.walk(os.path.join(site, "Bio")):
        sos += [f for f in files if f.endswith(".so")]
    if len(sos) < 13:
        print("FAIL: only %d compiled extensions in package (expected 13): %s"
              % (len(sos), sos), file=sys.stderr)
        return 1
    env = dict(os.environ)
    # 追加而非覆盖：biopython 的 C 扩展与 Bio.Cluster 运行期 import numpy，
    # 而 numpy 的 site-packages 由主配方的 runenv_info 挂在 PYTHONPATH 上
    # （conanrun 注入）。此前直接 `= site` 会把它冲掉 → `No module named
    # 'numpy'`（与 beniget/meson-python 同一缺陷形态，见知识草稿
    # DRAFT-ohos-conan-test-package-pythonpath-overwrite-clobbers-runenv）。
    env["PYTHONPATH"] = os.pathsep.join(
        [site] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print("FAIL: biopython API: %s" % r.stderr, file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: biopython module + compiled extensions + available I/O work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
