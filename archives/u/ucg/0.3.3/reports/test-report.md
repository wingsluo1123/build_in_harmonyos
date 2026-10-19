# ucg 0.3.3 validation

Native OHOS arm64 Conan create completed with exit code 0 on 2026-10-12.
Original registered inventory: 61 Autotest groups plus two GoogleTest cases.
Autotest: 59 PASS, two original XFAIL (28 and 30), zero SKIP/FAIL/XPASS.
GoogleTest: 2/2 PASS. One of the original cases is an empty upstream placeholder;
it is retained for inventory completeness, not claimed as added functional coverage.
Expected-outcome checks: 63/63; ordinary passes: 61, original XFAIL: 2.

Groups 28/30 retain their exact upstream glob-precedence assertions. Their
actual failure causes, expected/actual counts, empty stderr and source lines
are checked; crashes, missing commands, and unrelated errors are rejected.
Original performance tests use full Boost 1.58, Linux 4.8 source-search tree,
and the complete OpenSubtitles2016 English text. The 500 MB benchmarks and
all original ten-iteration comparisons run without denominator reduction.
Benchmark output diffs are statistics under upstream semantics, not asserted
zero and not claimed as cross-tool byte equivalence.

Installed-package consumers: 5/5 PASS (version, literal, regex, case-folding,
and no-match exit status). Real native output is `CONSUMER <label> PASS`.

Evidence: released immutable run ucg-w3-r13-20261012-real-xfail-gnu-role,
Conan log SHA256 bf67c5d911705995612428f4a319d040b627112c861ba6737d24375dc9cf3410.
The old transaction remains FAIL because its controller expected the wrong
consumer output syntax. It is NOT relabelled as W3 PASS. A new official finish
run was completed as ucg-w3-r14-20261012-official-finish: scoped W3 PASS, all
12 phases committed, task processes absent and release/postrelease PASS.
Official W3_local_ci exit code 0, integrity ede114f5fe0f5fcb, full log SHA256
97b5b8efa505489bdd0a80e3d2535809aed1a9ddebb4b8015ae955751d761e77.
Actual CI package binary SHA256
4d6980b9e76aaeb85773078deeb4b148ea6e47d567f2f1ac77b5e4426887ac3a.
Native aggregate finish RC1 is preserved: only post-W3 step5b/step8 false,
package verify and W3 local CI true, runtime inputs unchanged. The current
knowledge pair and submission contracts handle these post-W3 readiness gates;
no aggregate finish, platform worker CI or review success is fabricated.
