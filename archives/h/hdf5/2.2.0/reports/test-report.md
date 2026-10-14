# HDF5 2.2.0 native parallel C/HL/tools verification

## Historical complete verification — r038 (actual review repair)

Same-run original3216/3216 PASS, failure/skip/not_run/disabled0; real MPI
consumer1/1 and Harmony overflow-stream1/1. Original finish/native Conan RC0,
launch1, full receipts and release/postrelease owned0. Tested HEAD
4ae0c91b47a624a986458a997a776bb7d4762bb7; production candidate tree
3f7d0462d9987d815ae2660ea841cbd45878270f. Original JUnit SHA
639430ad424201a34e5723f40e4f4211edbd1c2529f57ff5e0b7e87fda93f0af;
raw W3 log SHA cef1aea1dcd53346fb71267952bb12548ac128157619cd1801f45af14510a729;
independent observed SHA f2d0beed3489853b912bca8211acd62048af5ef3376bd9ed5a59900f76f05114.

Review192997664 identified inconsistent platform guards in the production
temporary stream helper. The precise repair removes the function-body-only
guard, keeps POSIX mkstemp/unlink/fdopen, default tmpfile fallback when TMPDIR
is absent/empty and fail-closed invalid configured roots. Official19-patch
replay and separate Linux four-case controls are preserved; host controls are
not target coverage. Current platform CI and post-push review remain required.
Old r037 failed before launch and is independently retired after actual boot
drift, without target test results. No old transaction or partial PASS is replayed.

## Historical complete verification — r036 (before current review repair)

Same-run original3216/3216 PASS, failure/skip/not_run/disabled0; real MPI
consumer1/1 and Harmony overflow-stream1/1. Official finish/Conan commandRC0,
unique launch1, complete receipts and release/postrelease with owned processes0.
Tested HEAD af79b4f3788c24b502f0471bcd59b13cebabf0ef;
candidate tree e5c1520e629e3805360cd3e69fdb3dd1b8c95ebc.
JUnit SHA b4c338d864d28d3e4c250ecb803483bbd7d4898c215d377409afe8add4853874;
raw W3 log SHA e0af4307df974898a61c371d64e877f99063cfe319883604024deaf7186ce466;
independent observed SHA a06965c9b6a68f0545f40358ff6c24a1729a89ee05d693cd1d780f5ec9f7f192.

r035 passed all3216 original cases but failed the actual-UID temporary-file
oracle on HMDFS; the entire run remained FAIL. r036 retains that C oracle,
payload/read/EOF/unlink/nlink assertions and uses an exclusive0700 child of an
actual-process-owned POSIX parent, with no symlink, traversal/write and exact
cleanup checks. It does not replace process UID with projected storage UID.
No accounts, permissions, system services or foreign task roots were changed.
The older platform flush-refresh timeout's precise cause is still unproved;
these local results are not current-platform CI, publication or submission PASS.

## Historical complete verification — r034

Nineteen official refresh-patch --auto patches were strictly replayed and
executed in fresh run `hdf5-official-local-ci-220-20261010-r034`. Original finish
W3 local CI and native Conan create both returned0. Same official source as below.
Original full CTest inventory **3216/3216 PASS**, failed/skipped/not_run/disabled0,
including four actual Bash H5SHELL groups. Same-run MPI consumer1/1 and Harmony
installed production h5tools anonymous/unlinked overflow-stream1/1 PASS.
No across-run splice; the consumer uses actual two ranks and real file I/O.

Inventory SHA `b403ec060dd1e0f72b4894d0192bfbdf16a7ca6f7f3e6c1278aad79b90c3454d`.
JUnit SHA `b15ea92aff6c2e3b1153563fd02769899d079bff7e94ab8d4fe96c35cf69a2a2`.
W3 log SHA `beef5be2220b66ef3ae352cb0bc501bd588644332b10870971b836d87356ba95`.
Original automatically generated marker SHA
`51005999ca8dda9c67e0f02c6665d3d695ffad7604a6b5b64abd393bdecd6832`.
Independent observed SHA
`6ea6b261720e83f96f75ff9720498c3515958339b9baf52803e978b6f17caeb0`.
Unique launch1, twelve receipts/twenty-four WAL records; release/postrelease own0.
Old r0333215/3216 failure is retained. Two precise TMPDIR fixes preserve original
data/output assertions, not disable Bash or reduce the registered denominator.
Static parallel C/HL/tools only: not C++/Fortran APIs, platform CI, publication,
FEniCS complete stack or committee approval.

## Historical narrower verification — not the current complete denominator

Final official seventeen-patch representation, original source SHA-256
`1a1ab8209b35586fbc1aa279ba76d102130b95badcb20ca329587219112d8c16`.
Run `fenics-hdf5-disabled-diagnostic-20261009-r030` used fresh transfer,
one launch, an isolated Conan home and actual native `conan create` (RC0).
Published dependency resolution used `--build=never`; no dependency source build.

| Required inventory | Passed | Failed | Not run | Disabled |
| --- | ---: | ---: | ---: | ---: |
| Original configured CTest cases | 3212 | 0 | 0 | 0 |
| Real two-rank MPI HDF5 consumer | 1 | 0 | 0 | 0 |
| HarmonyOS installed-tools overflow stream | 1 | 0 | 0 | 0 |

The consumer is the original test_package `main.c` through
`mpiexec -n 2 ./real_parallel`, not a one-process MPI stand-in.
The platform-specific test calls installed production h5tools code, writes past
4096 bytes and checks an actual anonymous/unlinked private stream, complete read,
EOF, close and no task-directory leak. It verifies HarmonyOS and an owned TMPDIR.
Both commands ran inside the same successful native `conan create`.

Original inventory SHA-256:
`54970fecc190f7ae5b9babd27ca16887d9492e63714c51068b8660a4f0e12486`.
Original JUnit SHA-256:
`80f41cd130c41f266b66084cd3414b099f70b8bb8a1aa5472a1fa6ea12773f89`.
Complete create stderr SHA-256:
`063749f3c739fcd61130bd0a1d4dbc221ca20ad7bcd753a3bebc690a998ac444`.
Independent receipt/WAL audit verified a unique launch and release/postrelease
with no remaining owned processes. Raw logs and immutable receipts remain outside
the PR in the task evidence directory.

## Historical system-shell validation — r605 (2026-10-11)

Fresh immutable r605 executed the original enabled 3216 CTest IDs, including
all four original POSIX shell groups, with zero failed, skipped, disabled or
not-run cases. Native official Conan command RC0, MPI consumer1/1 and Harmony1/1.
The OHOS recipe binds the actual system `/system/bin/sh`; all original assertions
and timeout budgets remain. This result belongs to its historical candidate;
the current objcopy repair is independently validated in r760 below.
Independent observed SHA256:
`43e45accf1a6bce13a74113cc2a4970e99acece68a07eb9b3686af5fd1431511`.
JUnit SHA256:
`7e049a0727786e7486ef5bedeb7cbac0dbd24502939174a292177acfc5bcfce9`.
Actual full log SHA256:
`0a24d704e6bb30ec25b28f024941e0a3c548d2d97d8c92adf26fbc044953bf89`.
Unique launch and release/postrelease with owned process0; not platform CI PASS.

## Current objcopy review repair: r760 (2026-10-11)

Completed actual review identified a consumer defect: generation ignored the
configured compiler_executables objcopy and required a PATH-only tool. It now
uses the configured tool first, then the original PATH fallback. Only the stream
fixture comment changes from 2048 to 4096 bytes; assertions are unchanged.

Fresh r760 tested parent HEAD 348acecc259c9bd56410f1aef982e694ef1412ad and
candidate tree 5b09dcbf222a9b74fab271797eff95b2270c6040. Native official Conan and
original local CI RC0; original3216/3216, MPI1/1 and Harmony1/1 zero failures,
errors, skips, disabled or not-run outcomes. Independent observed SHA256
f83385995f1ced4af4f9b32cc664505d0d8e40594d4ef93b1e7decf937038197;
JUnit bbbaa4d1589df07fc3d0f977f2e63a0d6599c936eae753f9ab504f83a494c113;
local CI log e7ef324ce9711f785b6a8131fbff0267889759a21503843a09ee82dfcdaf0497.
Unique launch, complete receipt/WAL, own0 and release/postrelease independently
verified. Original generated marker bytes remain unchanged. Historical r605 and
3212 scopes do not certify this candidate or its future platform CI.

Scope is static parallel C/HL/tools. C++ and Fortran APIs are explicitly not built;
3216 is the complete enabled upstream inventory for this configuration, not all
possible HDF5 configurations. This is not publication, platform CI, FEniCS
whole-stack verification or committee approval of the high-difficulty application.

## Review metadata correction (2026-10-11)

Actual complete AtomCode review193197637 retains its original report and
evidence-backed adjudication. Current production has nineteen official patches;
the recipe's older "seventeen" comment was corrected to "nineteen" after actual
review193205665. The recipe AST is unchanged; no executable expression changed.
Frozen test_package/MANIFEST.yml retains its original
r030 bytes and is not a current execution receipt. The current same-run r760
3216/3216, MPI1/1 and Harmony1/1 results and hashes are listed above and in the
version manifest. No executable runtime input or original receipt was changed.
H5Fcreate/H5Dcreate2 are collective in the shared communicator: both ranks must
participate. The suggested rank0-only creation is not applied. Added-file patch
strip0 preserves actual patch-ng creation paths; no oracle or patch changed.

The POSIX temporary-file recommendation is outside this recipe's validated
Linux/OHOS scope. Windows is explicitly rejected by validate(); this PR does
not claim a Windows tools port. The original report is retained, not silently
marked as a tested Windows fix. Historical r038 and r605 headings are now
explicit and the original MPI consumer sentence is restored. This metadata-only
repair does not transfer older platform CI success to the new HEAD.
