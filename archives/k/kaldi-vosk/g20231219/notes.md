# kaldi-vosk g20231219

## Identity and scope

Pinned upstream: alphacep/kaldi commit
`2b69aed630e26fb2c700bba8c45f3bd012371c5c` (2023-12-19), Apache-2.0.
This is the Vosk Kaldi fork, not kaldi-asr/kaldi g20231112 or the vosk-api wrapper.
The recipe builds the 22 modules selected by upstream CMake, including the CPU implementation
of cudamatrix, online, online2, chain, nnet/nnet2/nnet3 and rnnlm. It installs
headers, shared/static libraries and CMake metadata. CUDA and the example CLI
programs are outside this library/CPU task; no registered tests are removed by
the adaptation. This is not coverage of every optional CPU extension.
The upstream CMake generator already excludes the optional KenLM files
(`kenlm.h`, `kenlm.cc`, `kenlm-test.cc`); this recipe retains that upstream
configuration. Upstream root CMake also does not add the optional SGMM2 module,
whose three tests are present in the source. The full library test-source
inventory is 129; 125 are registered/executed and passed, and four optional
tests are unexecuted. Full-inventory P/N is 125/129 (96.90%); configured-suite
P/N is 125/125 (100%). See `upstream_tests_report.md` for the four filenames,
upstream selection rules and a reproducible 129-to-125 inventory.

Published dependencies: openfst/1.8.4 (PIC static) and openblas/0.3.34 (ARMV8,
BLAS plus LAPACK, built with the published Flang toolchain). Native dependency
installation used the official OHOS armv8 profile and `--build=never`.
Shared OpenFST was separately probed and has no matching published binary;
the recipe therefore consumes the already published PIC archive.

## Changes and reasoning

1. Reuse the applicable OpenFST 1.8 API migration from kaldi/g20231112, after
   comparing it with this fork. Many Vosk APIs were already migrated. Remaining
   changes cover fixed-width aliases, FST_FLAGS, ArcMap, uint64_t properties,
   string_view-to-string conversion and std::make_unique. Two upstream test
   source files receive the same API spelling changes, preserving assertions.
2. Bind the installed OpenBLAS `lapacke.h` declarations and `LAPACK_*` macros.
   The macros carry the compiler ABI's hidden Fortran character lengths;
   `KaldiBlasInt`, `lapack_int` and `blasint` widths are checked at compile time.
   This intentionally differs from the historical CLAPACK prototype workaround.
   Both precisions exercise GEMM, inversion, SVD and packed LAPACK operations.
3. The upstream Python CMake generator now uses Python3, checks its return code,
   exports HAVE_OPENBLAS to consumers, and separates snapshot identity from the
   numeric CMake package version. CMake resolves the existing dependency targets;
   it does not download/build dependency replacements.
4. The native CMake distribution detects ELF without defining shared-library
   SONAME/RPATH flags. A linker capability probe enables those flags when absent,
   preserving real OS identity. Runtime DT_NEEDED names no longer contain build
   paths such as `src/matrix/libkaldi-matrix.so`.
5. Static OpenFST repeated in Kaldi DSOs registered multiple destructors for
   preempted FST_FLAGS_tmpdir. The initial upstream run had 102 PASS / 23 SIGTRAP
   at process exit; the independent decoder also computed the right transcript
   but exited abnormally. Diagnostic __cxa_atexit tracing proved that hmm and
   fstext registered the same string object twice. Shared builds now put all
   libfst.a objects into exactly one `libkaldi-fst-runtime.so`. Consumers inherit
   OpenFST headers without re-linking the static archive. No exit-handler,
   allocator, signal or assertion suppression is part of the package.

## Test contract

`KALDI_BUILD_TEST` appends `-UNDEBUG` to both library and test compilation,
so Release optimization does not remove assert/KALDI_ASSERT checks. Earlier
Release runs are retained as execution evidence; final acceptance uses assertions.

`build()` enumerates and executes all 125 upstream CPU CTest programs and fails
on any failure, skip, missing entry or abnormal exit. It saves the original
JUnit, inventory, log and machine-readable totals under `res/verification`.
The 125 entries are the current source/configuration, not the historical 123.

`test_package` links the installed CMake components. It checks independent
float/double numerical references, MFCC/fbank, streamed features, two concurrent
feature pipelines, FST composition/serialization, real acoustic model/iVectors/
lookahead/Nnet3 decode, PCM chunk boundaries, silence, missing-model errors and
repeated dlopen/API/dlclose through a separate shared consumer.

The original small English model and WAV are immutable downloads with SHA256.
The published OpenFST core lacks optional ngram extension headers. Test-only
unmodified bitmap-index/nthbit helpers and ngram headers come from the official
1.8.4 source archive; all FST core code remains supplied by the actual package.
They let the consumer read the original compressed Gr.fst natively, without
running acoustic inference or graph decoding on the host.

Linux reference for the fixed WAV:

| Grammar | Transcript | Frames | Acoustic cost |
|---|---|---:|---:|
| Digits | one zero zero zero one nine oh two one oh zero one eight zero three | 277 | -912.6262207 |
| Original full LM | one zero zero zero one nine oh two i know zero one eight zero three | 277 | -915.4348755 |

The full LM makes two substitutions against the spoken-digit human reference
(2/15 WER). That measured model behavior is reported separately from portability.
Native text/frame references are exact; acoustic score tolerance is 0.05.

## Validation status

Linux shared/static and native OHOS shared/static each passed all 125 configured
CPU programs with ordinary assertions enabled, no failures/skips/unexecuted tests
within that configured suite. The full 129-source inventory retains four
configuration-excluded/unexecuted tests (125/129, 96.90%).
Native shared and static installed consumers each passed 53 checks. The exact
W3 shared package passed 53 relocated upstream-CMake consumer checks; one
libkaldi-fst-runtime.so defines FST_FLAGS_tmpdir, with no libfst.a consumer link.

The current baseline W3 gates ran through a task-private Bash syntax adapter;
original scripts, syntax diff, 77 input hashes, logs and the original writer's
receipt are retained. A prior W3 startup syntax failure and later readiness
deferral remain separate. Original step35 and step8 methods completed their
respective retries; no historical exit code or CI receipt was fabricated.

W3 package: `kaldi-vosk/g20231219#41624dfd2949e97cc77b0de95bd6a949:6da0d3cbcc98fc8dc9a003e1f6e7e42e7f87cf3b#5d0e4a5ccd5e3c90e34ce993d2b8662c`.
Static package: `kaldi-vosk/g20231219#8b4a864c9c6d7b6333ff845aea104a98:96f7fd768bdfbcccb0e6a305b1b75de302d86b46#c42b36f2f474ccea598245117897c10f`.
W3 log SHA256: `c8ccf0ce857d000db0d1a0319cdebf28c90cbb8de9998513e924d70223ef9da8`.

PF9 currently rejects software-level README/manifest required by CONTRIBUTING
and SKILL. This tool/spec conflict remains a submission blocker for maintainer
confirmation. Final independent W4 review is retained in reports/audit-result.json.
Publication is authorized by the participant on 2026-10-04. Remote PR/Issue
links and CI status are tracked in the PR. C remains a candidate; the separate
B2 candidate corrects existing LAPACK guidance and has no pre-awarded score.

## Reproduce on HarmonyOS PC

```sh
conan create archives/k/kaldi-vosk/g20231219 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=kaldi-vosk/*
```

The device must provide the official native toolchain, Python3, CMake, Ninja
and binary-sign-tool, plus `timeout` supporting `--signal=KILL` for bounded
consumer execution. Conan supplies the declared libraries. Use a writable
task-local TMPDIR and the application-private executable filesystem.

The finish W5 completeness scan also flags four existing multiline KV fields in
E219/E253/E305 as empty by inspecting only their `|` first line. The official
KV parser reads their actual content and graph validate passes. Baseline
identity and the original rc=1 are retained; full finish is not all-green.

## 编译结束与知识候选

Native engineering acceptance completed on 2026-10-03; full finish retains the
W5 parser conflict described above. Source unchanged after native acceptance.
The 2026-10-04 B2 follow-up adds knowledge/drafts/E429-draft-8A28.kv and .md,
with a standalone vendor LAPACK ABI probe in knowledge-reproducer/.
This explicitly corrects the closest existing LAPACK310 draft; it does not
claim invention of LAPACK macros or first discovery of hidden CHARACTER lengths.
The new probe passed on the same native published OpenBLAS package (kv035).
