# KSyntaxHighlighting 6.18.0 device verification

Device: HarmonyOS PC AArch64, Clang 15, Conan 2.29.1. The package was rebuilt
from the archived source with `CONAN_HOME=~/work/psj/ch-ksyntax-highlighting`
and `-c tools.build:jobs=2`; `conan create` exited 0. The recipe ran the
upstream tests inside `build()` before packaging.

Final device rerun on 2026-10-15: `conan create` exited 0 and produced
`ksyntax-highlighting/6.18.0#7051f79ba210a55bc6e6a304ec6128eb:57ffd8c720a5bfee7e8827990cd6550a49181c1b#06f3de314fc65f6186756cd92277f74e`.
Normal CTest passed 6/6 in 27.15 s; the upstream `BENCHMARK` configuration
passed 2/2 in 178.35 s. Neither CTest run reported skipped tests. The consumer
test was rebuilt and executed through `self.run`, printing its PASS result.

| Upstream CTest entry | Qt Test PASS records | Failed | Skipped |
|---|---:|---:|---:|
| wildcardmatcher_test | 22 | 0 | 0 |
| repository_test | 114 | 0 | 0 |
| theme_test | 38 | 0 | 0 |
| testhighlighter_test | 288 | 0 | 0 |
| htmlhighlighter_test | 288 | 0 | 0 |
| folding_test | 288 | 0 | 0 |
| highlighter_benchmark (`BENCHMARK`) | 288 | 0 | 0 |
| repository_benchmark (`BENCHMARK`) | 99 | 0 | 0 |
| **Total** | **1425** | **0** | **0** |

The final normal CTest run reported `100% tests passed out of 6`; the separate
benchmark configuration reported `100% tests passed out of 2`. The 1425 Qt
Test records include
framework setup and cleanup records, so the CTest and Qt Test totals are
different counting levels. The test registration source is
`autotests/CMakeLists.txt`: the first six entries always run; the two benchmarks
are explicitly registered only for `CONFIGURATIONS BENCHMARK`, with an upstream
comment that they should not run during normal testing. The recipe invokes
that configuration separately to execute all eight registrations. Optional
AppStream metadata validation was not registered because `appstreamcli` is
unavailable. No registered upstream CTest entry was skipped.

The Conan `test_package` configured and linked against
`KF6SyntaxHighlighting`/`KF6::SyntaxHighlighting` and executed its binary via
`self.run`. It found the embedded C++ syntax and Breeze Light theme and exited
0 (1/1 consumer program).

The detailed Qt Test rerun used the same six device binaries. A deliberate
control run without the private Qt runtime path failed all 6 at ELF relocation
with missing Qt symbols; with the Qt package `lib` and build `bin` in the
test invocation's `LD_LIBRARY_PATH`, it passed all 6 with zero skips. This
control does not change the successful `conan create` result.
