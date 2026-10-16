# mrtparse 1.6

This is a pure Python MRT routing-record parser. The task board labels #8998
as cpp; the actual source is Python and is being prepared through the existing
human contest route. No task language, worker gate, or protocol is changed.

The pinned PyPI sdist is 34,122 bytes, SHA256
`9bc87a1237a0ab6e922aecd17061d9d65ccb09c02a1294114a7fdb8bd0c3a7e5`.
Its module equals upstream v1.6 commit
`9851c487c209014cc94b7495dbf7796a312b0da0`. The sdist omits LICENSE;
`LICENSE.upstream` is the actual LICENSE blob from that commit, Git SHA1
`e06d2081865a766a8668acc12878f98b27fc9ea0`, SHA256
`cb5e8e7e5f4a3988e1063c142c60dc2df75605f4c46515e776e3aca6df976e14`.
The module uses only Python standard-library modules. H1-002 now records actual
HarmonyOS aarch64 / Python 3.12.9 loading of the Conan package; metadata-only
Python supply was not used as runtime proof.

The original BGP4MP_ET branch calls Reader.val_num(4) while Reader.buf is None.
Simply providing that buffer would also leave the prefix in the child decoder's
input. RFC6396 section 3 places the 4-byte microsecond field at the start of
the payload, included in its declared length. The patch checks its length,
decodes the actual payload prefix in network byte order, and passes only the
remaining payload to Bgp4Mp. It preserves ordinary BGP4MP and raw Mrt.buf.
Short prefixes produce the existing MRT Data Error result instead of TypeError.
This parsing defect is reproducible on Linux; it is not an OHOS-only ABI bug.

The complete fixed v1.6 repository tree has no automated test suite. It does
provide five example scripts and 12 sample inputs. The recipe packages these
unaltered files with the module; it does not run setup.py's temporary symlink
installation. The consumer validates those 12 inputs with unchanged summary.py
and checks their original-source error boundaries. Of 382 records, the 31
BGP4MP_ENTRY records in openbgpd_rib_table-mp are documented unsupported inputs;
they remain MRT Data Error results, not successful decodes. No sample is dropped.

WSL Ubuntu x86_64 / Python 3.12.3 local evidence: five added unittest consumer
methods passed (0 failures/errors/skips), and all 12 sample comparisons matched.
Subtests and assertions are not additional consumer counts. These are host
results, not OHOS evidence. The separate H1-002 target consumers/samples and
official W3 now passed. Complete finish, independent W4, AtomCode, official
remote CI and valid review submission remain pending.

The package exports PYTHONPATH for lib/python and no CLI binary. No commands.json
is declared. Its Apache-2.0 source license is preserved. Source downloads and
local MRTPARSE_SOURCE_ARCHIVE inputs both retain the exact sdist hash check;
Conan export_conandata_patches/apply_conandata_patches carry the fix.
---

**编译结束**: 2026-10-13 21:52
**最终状态**: built


## 对话记录 / evidence reconciliation (2026-10-13)

The original secondary asked the author to consume H1-002 RESULT and exact error
originals, reuse valid tests, and fix only necessary private candidate gaps or
record a precise HOLD. It explicitly excluded replays of 001/002, host/full H1 or
review, official script edits, PF9 bypass, publication, claims and shared windows.

H1-002 executed one official finish (rc1, owned PID/PGID gone). The actual target
Python 3.12.9 Conan module hash is
514d7f5309bf8ec00efbf54dfa6b1d257f88b05446973ca1abb631c42049e9d2.
Five consumer methods passed without failures/errors/skips. All 12 unmodified
samples match the original-source baseline: 382 records, 351 decoded and the same
31 documented unsupported BGP4MP_ENTRY records. The target W3 setup/build both
returned 0, JC prdiff checked all 13 input files, and the real destructive negative
test moved lib/ away and confirmed consumer failure. L2 skipped because no bin/
exists for this library; this is not a failed CLI test.

Raw evidence stays immutable under evidence/h1-002 and h1-002-consumed in the
private author directory. RESULT SHA256 is
90b7a05eaa91a1cb733091619a8e7d37d6fb6d6ccb3d61ca101fbfcd27b40aa5;
W3 log SHA256 is
5438bfe03ba5e1d477a6476fb403e2c9ab8288fd4349c4893fc0cadac6f353e9,
matching the official .ci-result.json. That machine marker was not rewritten.

The author corrected only documentation/metadata, including the applied-patch
count and generic bugfix classification. The exact H1-generated patch and all
Conan/test inputs remain byte-identical to H1-002. No software or review rerun.

## Fixed-source support correction (2026-10-14)

The original finish rc1 and step5b FAIL remain historical results. Fixed baseline
f6a25613daaf1aec7170321c249d6ccf3f329593 support shows that the four exact fields
E219/root_cause, E253/root_cause, E305/root_cause and E305/rec_approach have nonempty
multiline values (official parser lengths 316, 513, 244 and 806). W5's first-line
check misreads their leading |; this scoped correction does not claim global W5
PASS or alter other libraries' knowledge files.

SUMMARY is a warning in finish step6, whose recorded flag is True. Its exact
mrtparse full-scan failure follows 7840 valid manifests: the fixed qpdf 12.3.2
manifest (SHA256 ac7e10b841946fe73087e0b4336eb0a5218411d24a24a788c748c0b7af87eeff)
contains duplicate knowledge_gained keys, and summary.py:89 appends to a string.
It is not a mrtparse defect or step8 failure. Step8 is submit readiness and still
checks legacy packaging and .staging-verified. No qpdf edit or scan rerun occurred.

G0 configure127 is retained from clean_verify's unconditional configure/make/
DESTDIR route on a pure Python library; finish logs it as a warning. R19/R20
requires Conan and deprecates manual tar/DESTDIR. The limited support disposition
therefore reuses the real Conan package, installed consumers and W3. No manual tar,
empty staging marker or repeat software validation is needed for these findings.
The 2026-10-14 bounded internal pure-library readiness disposition now accepts
those original installed-consumer, negative and W3 results. The inspected driver
marker only checks bin/ --version; no marker is created. This decision is not an
official waiver or complete finish/W5 PASS.

The required software-root README remains present, while exact PF9 source rejects
that four-layer path before branch lookup. Formal W4/full AtomCode, applicable B04
knowledge consumption and actual publication/platform gates remain separate.
Support RESULT SHA256 7228a09e18924beeb8fd1658e8db0b9c28b79f8508f34fadb983db0427cdab3c
and primary limited disposition SHA256
15fcda9e9d030e7f01f1899d819f70be0279d442a7efbd60d16c259fcb80889c bind these corrections
to candidate-003 and this fixed baseline. Candidate-005 separates final PR contents from local material inventory, excludes
ci-metadata.json and reports/, and adds the paired draft below. Tested patch, Conan
inputs, consumers and samples remain identical. The genuine target report and logs
remain in the author local evidence; this note carries their accurate summary. The complete process rc1 takes precedence over .handoff text; built does
not establish complete finish, valid submission, merge or points.

Paired knowledge draft: knowledge/drafts/E429-draft-78B3.kv and E429-draft-78B3.md. Generated through
fixed graph add --draft; original Type17 traceback actually matches the fixed
parser/engine isolated preview. It remains a draft; knowledge_ref is not assigned
a formal E number. Original limited-readiness disposition SHA256:
cda35e25167245bec69ea4668f64c756d1f2cef2880db2f8c35481ce2f8797e1.
