# qpack 0.0.21

Task9897 / orrkri / new A+B. Official source is PyPI sdist SHA256
f953e9f7d4d0946c10909c4a1de307d8d265f315b7b86c4af18b9ef1567ec845,
corresponding to upstream tag commit e55af6e2e7c8071a8533f4395682ddfb0b3018ce.
Core C/Python/test bytes match the tag; sdist setup.cfg adds egg_info metadata.

Only the Python3 PY_COMPAT_COMPARE macro changes: a -1/0/1 comparison result
becomes an explicit equality predicate. Otherwise the six UTF8 aliases OR
together always select UTF8 and the Latin1 branch is unreachable. The real
C extension is retained; no fallback-only success claim or unrelated integer
or arbitrary-codec contract change is intended.

The official POSIX refresh-patch command actually generated
patches/0001-qpack-_qpack.c.patch, SHA256
7ea40c69494ef654b2667dc6a045c9f6bb5b55d5c5b0392f7cd1207db1cfd6a7,
with one added and one removed C line. Independent application reproduced
the fixed C SHA256 92add8b4eb194aad506a4367167fe675e9d41bfe6ee8485278a8e850efd4e5a4.
The patch bytes are unchanged. It is a generic Python3 bug fix, not an
OHOS-only change; the upstream PY_MAJOR_VERSION >= 3 branch remains intact.
The public manifest retains tool hashes/time but omits private device paths;
the complete original metadata remains in the H1 evidence.

E227 applies to four empty context lines in this canonical unified diff:
an outer git diff --check flags their required single-space prefixes. The
original rc2 is retained. Non-patch whitespace and real patch parsing are
checked separately; Git apply --check and GNU patch --dry-run --fuzz=0
both returned 0 on the original source. These are input checks, not software
build/test results; no source or patch was altered to suppress the warning.

The recipe built upstream setup.py with hash-pinned setuptools84.0.0 in a
private source directory and the exact published Python3.12.9 dependency.
Actual target import, native compile/link, OHOS signing and package C loading
completed. The signed package extension SHA256 is
73974079526667ecba9aa984b53dd7abe66fb80563c1c9f9bb65c730337d5728;
SOABI is cpython-312-aarch64-linux-ohos. No global install was performed.

The unchanged original C source produced UnicodeDecodeError for 0x81ff/latin1
while fallback returned U+00FF. Observation rc0 means that the defect was
collected; the original software did not pass.

Upstream test census: test/qpack_test.py has exactly 9 unittest methods, SHA256
209a077bfbdf4f152ad7dca05cfcf643167d2c1f111bf91189a127f75c309f6a.
All 9 ran and passed, with zero failures, errors or skips. No assertion was
removed or relaxed. One additional real native-package consumer passed its
4 groups. Alias rows and internal assertions are not extra programs/methods.

Independent conan-verify returned 0. Its G4 package-ID warning and skipped
L2/L4/L5 checks are retained; separate actual package collection verifies the
artifact, but does not convert skipped official checks into executed PASS.
The earlier formal W3 setup returned 0 and build_and_test returned 1: its full repository
JC1/JC5 checks hit the same five historical baseline markers. L1/L2/L4/L5 were
blocked_by_JC; no .ci-result.json was produced. The sparse Git object stderr
is also retained. This private native result is not official CI or submission.

Original H1 RESULT SHA256:
4994a494b7dc496e0c9341c5e3b6ff62bd037ebc4dc03778b7947d863059e8ad.
All 125 collected raw files were independently verified; this history is retained.

On 2026-10-09, W3-only-002 naturally completed with worker rc0 and no signals.
The official setup and build_and_test both returned 0. JC used the fixed full
13-file input in prdiff mode with zero errors. L0/L1/L4/L5 passed; L2 skipped
because this library has no bin directory. W3 ran the unchanged original suite
9/9 and one native consumer with 4/4 groups, with zero failures/errors/skips
in the original suite. Its natural .ci-result.json reports W3_local_ci rc0,
and the retained log SHA256 is
d58d01923d04a752fc738644062f2bcc6621bac45b52bddd7e0eca395c6e1cca.

Actual W3 package reference:
qpack/0.0.21#d609ddcbb5c8229e8df59e966278c1a7:6b129b068851896169fae42d399fa922d239ce8a#ef9e6d61083bd36acff907cb26d551ae.
Previous standalone reference, kept separately:
qpack/0.0.21@ohpcd/stable#48355bd4f927709784e4e14c95d2655b:6b129b068851896169fae42d399fa922d239ce8a#ef9e6d61083bd36acff907cb26d551ae.
These have different channel/recipe revisions, although package ID, package
revision and signed extension bytes match. W3 logs record source predownload
rewriting before export; this suggests the recipe revision change but is an
inference, not a claim that the two references identify the same package.
The frozen source/recipe/patch/test input bytes remained unchanged.

W3-only-002 RESULT SHA256:
93eefd0a403b1312eb6ac30b4eda73aa6afdd96eaf50db05b32c436d7bab0a35.
Both collected archives and all 40 raw files, including the six current
package files, were independently verified. Final review/AtomCode, publication,
binding, official PR CI and submission remain pending. Private W3 does not
establish official CI, acceptance or points; status remains archived.
