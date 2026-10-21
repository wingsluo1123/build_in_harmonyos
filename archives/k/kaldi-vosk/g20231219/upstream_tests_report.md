# Upstream test audit

Source: alphacep/kaldi `2b69aed630e26fb2c700bba8c45f3bd012371c5c`.
## Source inventory and configured execution

The pinned archive contains **129 library `*-test.cc` source programs**. This is
the upstream inventory N, including optional extensions, not a claim that 129
programs were built or executed. There are also two configuration probes in
`src/probe` (`exp-test.cc`, `mkl-test.cc`); neither belongs to the library test
suite. A raw recursive filename search therefore finds 131 files.

The original upstream CMake entry point selects **125** of the 129 library
tests. `test_package/MANIFEST.yml` lists these 125 registered programs with
their source and CTest command. The following four tests are present upstream
but **not built or executed** in this recipe's retained upstream configuration:

| Upstream source | Upstream selection rule | Current result |
|---|---|---|
| `src/lm/kenlm-test.cc` | `cmake/gen_cmake_skeleton.py` explicitly excludes `kenlm.h`, `kenlm.cc`, `kenlm-test.cc`; `src/lm/Makefile` enables the test only under `KENLM_ROOT` | Not executed; optional KenLM backend not enabled |
| `src/sgmm2/am-sgmm2-test.cc` | Root `CMakeLists.txt` does not add `src/sgmm2`; `src/Makefile` lists SGMM2 in optional `EXT_SUBDIRS`, with separate `ext_test` | Not executed; optional SGMM2 extension not built |
| `src/sgmm2/estimate-am-sgmm2-test.cc` | Same SGMM2 selection rule | Not executed |
| `src/sgmm2/fmllr-sgmm2-test.cc` | Same SGMM2 selection rule | Not executed |

These are existing upstream configuration boundaries, not four observed test
failures or four CTest skips. They are also not four passes. They remain a
coverage limitation: this package validates the upstream CMake CPU library
configuration, not all optional backends in the repository. Enabling them would
require adding/building the respective backend and running its original tests;
compiling KenLM without `HAVE_KENLM` is not accepted as meaningful coverage.
No adaptation patch removes a registered test or introduces these exclusions.

The previous PR incorrectly used 125 as the unqualified upstream total and
omitted the SGMM2 difference. Correct totals are **N=129, executed=125,
passed=125, failed=0, configuration-excluded/unexecuted=4**. Therefore overall
P/N is **125/129 (96.90%)**; the configured suite is **125/125 (100%)**.

Reproduce the source inventory without building, using the recipe's exact
source tarball and Python's standard library:

```sh
python3 verification-evidence/audit_upstream_test_count.py /path/to/kaldi-vosk-g20231219.tar.gz
```

`verification-evidence/upstream-test-inventory.json` records all 129 sources,
their SHA256 values, selection status, the two probes, and upstream build-file
hashes. The script verifies the archive SHA256 and checks the original upstream
CMake selection against all 125 MANIFEST source entries. Counting source files
is separate from the historical JUnit execution results below.

The two changed upstream test sources retain their inputs and comparisons:

- `fstext/determinize-star-test.cc`: OpenFST `Map` becomes `ArcMap`.
- `fstext/trivial-factor-weight-test.cc`: the same API migration for the two
  Gallic mapping calls; `RandEquivalent` settings and assertions are retained.

`KALDI_BUILD_TEST=ON` adds `-UNDEBUG` after Release's `-DNDEBUG` to both library
and test compilation. Ordinary `assert` and `KALDI_ASSERT` are active. The
upstream optional `KALDI_PARANOID` checks remain at their default setting.
Earlier runs with `NDEBUG` are retained only as process-execution evidence.

| Assertion-enabled configuration | Configured N | Executed | P | F | S | U within configuration | Exit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linux x86_64 shared | 125 | 125 | 125 | 0 | 0 | 0 | 0 |
| Linux x86_64 static | 125 | 125 | 125 | 0 | 0 | 0 | 0 |
| Native OHOS armv8 shared, clean Conan kv025 | 125 | 125 | 125 | 0 | 0 | 0 | 0 |
| Native OHOS current conan-verify shared | 125 | 125 | 125 | 0 | 0 | 0 | 0 |
| Native OHOS current W3 forced shared rebuild | 125 | 125 | 125 | 0 | 0 | 0 | 0 |
| Native OHOS Conan static | 125 | 125 | 125 | 0 | 0 | 0 | 0 |

For each row, P/configured-N and (P+F)/configured-N are 100%. Against the full
129-source inventory, each row covers 125/129 (96.90%), with the same four
optional tests unexecuted. Counts are test programs, not estimated counts of
internal randomized/looped assertions. Native W3 and static option
records are distinct complete runs, with exact identities recorded below.

The native package reference for kv025 is
`kaldi-vosk/g20231219#fdb4ae0bb2b3824a17b5ac1211773094:6da0d3cbcc98fc8dc9a003e1f6e7e42e7f87cf3b#bc28abece92e4f6f359b6ad2b1a146ab`.
The package includes `res/verification/upstream.xml`, `upstream.log`,
`upstream-inventory.json` and `upstream-summary.json`. The recipe fails if the
inventory is not 125, a process fails, a test skips, or an entry is unexecuted.

The independent installed consumer adds 27 scenarios and 53 explicit checks:
17 numerical/features/FST scenarios (29 checks), two model modes with three
scenarios each (14 checks), one missing-model diagnostic/exit check, and three
DSO lifecycle cycles (9 checks). Compilation and linking use the installed
public components. Native kv025 returned the expected exit for every command.
These consumer checks supplement the upstream suite and are counted separately.

Historical native execution: 102/125 then 121/125, with four later loader-path
retries. The original 23 exit-time SIGTRAP failures led to proof of duplicated
OpenFST global destruction. They remain documented and are not combined into
a fabricated single passing run. The complete assertion-enabled run above is
the acceptance evidence.

Final W3 shared reference: `kaldi-vosk/g20231219#41624dfd2949e97cc77b0de95bd6a949:6da0d3cbcc98fc8dc9a003e1f6e7e42e7f87cf3b#5d0e4a5ccd5e3c90e34ce993d2b8662c`.
Final static reference: `kaldi-vosk/g20231219#8b4a864c9c6d7b6333ff845aea104a98:96f7fd768bdfbcccb0e6a305b1b75de302d86b46#c42b36f2f474ccea598245117897c10f`.
The W3 shared and native static consumers each passed all 53 checks. Relocating
the W3 package and consuming upstream CMake exports also passed 53 checks.
W3 used the pinned current gate logic through a documented task-local Bash
syntax adapter; its original writer's log SHA256 is `c8ccf0ce857d000db0d1a0319cdebf28c90cbb8de9998513e924d70223ef9da8`.
PF9's software-metadata path conflict is recorded separately from test success.
