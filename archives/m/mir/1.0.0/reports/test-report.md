# MIR 1.0.0 — native OHOS ARM64 validation

Task15188, branch feat/mir-1.0.0; account2501_91199785, team诶，云朵.
Path A+B+C candidate only: committee acceptance, score, merge and publication
are not implied by this local report.

## Current CI92782 repair verification — r6

CI92782 (worker CI-003, HEAD2309bbf5) ended in compiler
`posix_spawn` EAGAIN / Resource temporarily unavailable. Source download and
all14 patches succeeded; missing predownload curl was not the terminal cause.
The same raw log exposed two independent portability defects: the signing
launcher rejected the source-local thread probe `__tmp.out`, and Make4.4
could not create its FIFO jobserver on the worker filesystem.

The launcher now checks linked outputs BEFORE invoking the compiler, permits
only the exact owned source/build roots, normalizes dotdot, and rejects
symlink parents and foreign paths. It does not permit their common parent.
Make uses -j1 and scoped MAKEFLAGS/MFLAGS, but MIR's original parallel
generation and bootstrap targets remain enabled. A successful build must
actually contain -DC2MIR_PARALLEL; silent feature downgrade is now a failure.
No upstream source patch, expected result or test inventory was changed.

Historical correction: old r5 genuinely completed its declared7544 identities,
but its raw log contains the thread-probe path exception and zero occurrences
of -DC2MIR_PARALLEL. Its original results and PASS receipts remain preserved;
they are not sufficient evidence that the conditional parallel backend was
enabled. Current r6 supersedes that capability claim, not the old raw records.

Recovered device10.62.210.132:2222, boot
12b3ceb3-5bf3-49a1-bb4d-00508715a64f, UID20020084; native
OHOS6.0/armv8/Clang15/Release, Conan2.29.1.

| Current formal linkage | Upstream executed / PASS | Installed consumer | result |
| --- | --- | --- | --- |
| shared | 7544 / 7544 | 1/1 | RC0 |
| static | 7544 / 7544 | 1/1 | RC0 |

Transaction mir-conan-w3-20261014-r6 completed all12 receipt phases,
release/postrelease and owned-process absence. Both actual variants enabled
C2MIR_PARALLEL; the complete log has62 compiler-macro occurrences, zero
signing-root exceptions and zero Make FIFO errors. The five bounded host
launcher/regression checks also passed, but are not counted as native tests.

- Formal log SHA256: ae9c0d873ed93e5142948e0499c52e62b1810c8d81395f3e9e0b90ed93082b9b.
- Receipts SHA256: ae56b0ebb2d65ccf92c26dbebf4f0bc341c31fbc545dd3df658fe357eb150c09.
- Inventory SHA256, both variants: 1d25a4d90f57ae16ce83238912cf206ea4109f10562e6a1b7d92ce17078c4ea4.
- RREV: c71b35b854c96b2998decbcae3a05097.
- Shared PID0726937e17000c634ad5fc029642008575bda6b0 / PREV9cbe081732d9487ab1240fe3967c593d.
- Static PID21b17f8b2bc0e9511e276e3d57a23893067cefe5 / PREV676bff31ff6d38b407a9882f54dbf7b8.

Official finish mir-finish-w3-20261014-r2 returned RC0. Conan verification
AND its independent local CI each passed7544/7544 plus consumer1/1, with
the parallel compiler macro enabled. G1-G4, L4/L5, scoped W5 and W2 passed;
all12 receipt phases and release/postrelease passed with no owned processes.
The optional legacy source-tree G0 tarball-location warning is not called a
PASS: both real Conan builds independently extracted the hash-verified
official archive via the normal source cache.

- Finish aggregate log SHA256: 5ba0d92f04a167dc0bdf0e51d5e871b58caa5f51c6f74134b2cb74870e7c202c.
- Finish receipts SHA256: f67e87776267b4d7e2449df83fc952a03435a6b5c086fadc19e89658d006bbd5.
- Official Conan verification log SHA256: e45b198c657d2febfa9b809a99cb6a12fce2fb67dd2b26b7eb783f810f7d32f2.
- Producer local CI log SHA256: c2eb4bb828a9dcc3803a781226e56cdd12ceda21d91d9e92530e769da337be53.
- Producer CI result SHA256: 605383ec26bf2e7fafcb0232edcbb5d8b1e2758faecc78181df17e764ba7906e; integrity9ff8eb7478244780.

The fresh producer outputs are copied byte-for-byte, not authored or
reserialized. Runtime inputs were independently matched against BOTH frozen
transactions before this documentation update; no old run is stitched into
the new PASS. Neither this repair nor native success claims to repair
worker-wide EAGAIN, platform Review, merge or publication. Historical r1's
post-W3 document failure and r5's capability limitation remain preserved below.

## Historical formal Conan verification (r5; capability limitation above)

Native OHOS6.0/armv8/Clang15/Release, Conan2.29.1, endpoint
10.62.210.132:2222, boot2488bc3f-f5fe-4b70-b131-07c630c7157b, UID20020084.
The configured compiler is resolved to an actual absolute executable; the
recipe owns source patching, ELF signing, build, upstream tests and packaging.

| Linkage | Upstream inventory / executed / PASS | Installed consumer | conan create |
| --- | --- | --- | --- |
| shared | 7544 / 7544 / 7544 | 1/1 | RC0 |
| static | 7544 / 7544 / 7544 | 1/1 | RC0 |

The same logical IDs run in both modes: the public test denominator is not
doubled. No registered case is skipped or accepted as an expected failure.
Formal transaction mir-conan-w3-20261014-r5 completed all12 receipt phases,
runner exit, owned-process absence and release/postrelease. Its frozen inputs
bind HEAD6425af51453d8c62913265f9a65a252499e0c42e and recipe candidate
b47ad184bd90be1d131c57a2532be5f0714d01bed37bffea5982d3f46c9d196a.
The submission adds reports/metadata afterwards; runtime inputs remain unchanged.

- Official source: https://github.com/vnmakarov/mir/archive/refs/tags/v1.0.0.tar.gz
- Source SHA256: fdc934db5c858ee9aa77c09e21a3ed19ddc243ae441eb4c9b08e79b203c34055.
- Formal log SHA256: d7dad87c0df2a050b23c33f712c38b056a353640a401e9e3f00081c85bc333e1.
- Receipt-chain JSON SHA256: 748b5aa6b4ab91c70790bbe8e6e881987bd76cf329e436da96dd37838f52cd49.
- Shared inventory SHA256: 1d25a4d90f57ae16ce83238912cf206ea4109f10562e6a1b7d92ce17078c4ea4.
- RREV: 00d52405a1c51fec7a37b0e2bef9febe.
- Shared PID: 0726937e17000c634ad5fc029642008575bda6b0; PREV: 809b6d6361c5b1660dd8a967bd6e3a09.
- Static PID: 21b17f8b2bc0e9511e276e3d57a23893067cefe5; PREV: 879330fa74fda50647ae838bcda11639.

Source bytes seed the task-private normal Conan download cache. source()
still extracts the official archive and applies all14 prescribed generated
patches. No patched source archive or prebuilt package replaces that process.

## Exact upstream denominator

7544 means independent execution identities, not7544 distinct source files:
49 ordinary leaf tests +8 bootstrap leaf tests +7487 source-case/mode pairs.
Six original C2M modes have1069 eligible cases each, and lazy-BB has1073,
according to the upstream architecture/option filters. The complete57 leaf
targets and all7 mode invocations are enabled. Discovery via original list
mode precedes execution; unique BEGIN/PASS IDs must exactly equal inventory.
Optional LLVM bridge and performance benchmarks are not configured or claimed.

Formal builds use -O3 -UNDEBUG so test assertions remain enabled. The earlier
exploratory GNUmake default used -O3 -DNDEBUG; its PASS is not substituted for
the stronger formal result. Each case retains its original expected stdout,
stderr and exit code. The supported diff presentation changes do not alter
the oracle. The three stale public API fixtures are updated to current1.0.0
APIs, and serialization uses a checked task-private TMPDIR roundtrip.

## OHOS-specific installed consumer

One composite installed-library test links mir::mir using CMakeDeps and
executes after binary-sign-tool signing and readelf .codesign verification.
Independent contexts exercise interpreter, eager generation, lazy-function
and lazy-basic-block generation, with cold/hot execution and positive,
negative, zero and >32-bit integer arguments. The28 numeric assertions are
checks inside one consumer, not28 separately declared tests.

## Architecture repair and failed alternatives

The ARM64 transparent BB callback saved Q0-Q7/Q16-Q31 but omitted Q8-Q15.
The first function compilation callback was a second independent boundary
with the same omission. AAPCS64 C callees preserve only the low64 bits of
v8-v15; that is insufficient for a live128-bit long double across invisible
callbacks or the generated program's stronger internal callee contract.

r15 had five lazy-BB failures. A BB-only repair in r16 passed4/5. r18 showed
the remaining second argument22.5 becoming0 (expected exit142, actual141);
r19 IR located liveQ8 across the first-call compilation before its real
callee prologue. Full-Q pair push/pop at BOTH boundaries, inverse restoration,
16-byte SP alignment and unchanged r10 save offset resolved the actual defect.
r20 then passed directed5/5, full7544/7544 and consumer1/1; the formal shared
and static result above independently reproduces the complete suite.

Formal r3 failed on Python posix_spawn of bare clang, repaired by absolute
configured tool resolution. r4 hit an inherited2400s aggregate Conan deadline;
late child output was diagnostic only and remains FAIL. r5 uses7200s per
Conan mode, with unchanged30s case and1800s group limits. No failed result was
promoted and no case was excluded, downgraded to double or sent to a fallback
backend merely to obtain PASS.

## Supported scope and safety boundaries

Only native OHOS ARM64 library/header artifacts are packaged. CLI executables
built for upstream testing are not installed. There are no Conan package
dependencies; libc, dl, pthread and m come from the platform.
C2M_SYSTEM_INCLUDE/C2M_TARGET_INCLUDE identify the real configured compiler's
system headers for non-embedded-header callers.

OHOS header compatibility consumes some Clang declaration annotations; it is
not an implementation of packed/aligned attributes, asm symbol renaming,
inline assembly or arbitrary GNU extensions. SVE/SME state and other OSes
are not validated by the Q-register repair.

E550-draft-MR10 generalizes hidden-callback state width and dual-entry
coverage for JIT/FFI/instrumentation runtimes. Four-scope dedup found related
HFA classification and soft-float word-order knowledge, not this mechanism.
HD3 is supported by an actual machine-code repair and causal runtime proof;
test count, duration and patch count alone are not high-difficulty claims.

## Official finish / remote pipeline

Official finish mir-finish-w3-20261014-r1 completed both Conan verification and
its independent local CI: each7544/7544 plus consumer1/1. G1-G4, L4/L5, scoped
W5 and W2 passed. The aggregate command returned RC1 ONLY at final step8:
reports/test-report.md was not included when the projection was frozen.
This report was prepared locally afterwards and now resolves that document
requirement. No runtime input changed, so no build/test replay is required
for this documentation-only repair.

Keep the states distinct: formal device W3 r5 PASS; official local-CI substep
PASS; aggregate finish PARTIAL_POST_W3/RC1; original finish transaction FAIL
preserved. Its release/postrelease passed with no owned processes. Neither
the aggregate return code nor the old receipts have been changed to PASS.
Current report/template/Issue/knowledge readiness is checked separately by
the blocking Pre-PR contract; a generic RC1 is never accepted.

- Finish aggregate log SHA256: ac4bfee0141b80c5773eabec76fe15f12ddfb53effb0fbf3bd5277b96d28a5a6.
- Official Conan verification log SHA256: 3cab9e486ac0f4d4cbfdacae4b2fab73ebb9bde76fe05842c2340a0ac6e2a4af.
- Producer local CI log SHA256: 5e5da953efae6c04637d65530722b349cea68965837b56878e50f1b3f92a54cf.
- Producer CI result SHA256: 38a71213e6976c322ac8879331ce1f5767044f174c8da22af6476826992ff887; integrity d0cedde70a046699.

The producer .ci-result.json and matching raw logs are copied byte-for-byte
as local submission authority, not authored or reserialized. Native original
logs/receipts remain in the task evidence directory. Public source, this
report and the upstream inventory permit independent reproduction; raw local
runtime state is not software source. Nonblocking G0 could not locate its
legacy source-tree tarball; both actual Conan runs independently extracted
the hash-verified official archive through source(). The notes-dialog warning
is historical metadata, not a build/test failure.

No worker CI, platform Review, merge or publication PASS is claimed here.
