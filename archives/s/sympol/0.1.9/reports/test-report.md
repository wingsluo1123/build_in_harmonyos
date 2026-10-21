# SymPol 0.1.9 — native shared validation

Date: 2026-10-15. Target: OHOS 6.0, arm64, Clang 15, C++17, one build job.
This report is not a platform CI/publication certificate. Official native
verification/W3 passed in sympol-review-201-20261015-r1, with all 12 receipts
passed and released. Official W3 log SHA256:
95f0431004587f01ccfcfadddaa1b8ba835628c8bbf5bc5756592fe9bbcccc2d.
Aggregate finish is PARTIAL_POST_W3 RC1 (step5b,step8), not full finish PASS.
Independent W5 and Pre-PR close the corresponding knowledge/submission gates.

| Scope | Upstream denominator | Adapted result |
| --- | ---: | ---: |
| contrib/test-sympol.pl original CLI regressions | 28 | 28/28 |
| test/test-rank.cpp original Boost.Test methods | 2 | 2/2 |
| Installed QArray API consumer | Supplemental 1 case / 4 assertions | 1/1 case, 4/4 assertions |
| OHOS installed CLI geometry workflow | Supplemental 1 end-to-end case | 1/1 |

The two original CTest entry programs are executed directly by upstream.py;
two entries must not be misreported as two leaf cases. The direct driver
resolves the real Perl executable and retains original inputs/assertions.
Optional Eigen/Bliss backends are not enabled or claimed.

Frozen run: sympol-review-201-20261015-r1. Candidate tree:
`83f74fa0410f67bfe8df123569be1b0edac8e03d`.
Both clean native Conan create rounds returned zero. Full 12-receipt validator returned W3_PASS
after release, with no owned child process remaining.
Combined log SHA256: `2fca1f2709cd0b0b4246fa6e6ad54b42e66b2e65644a9acc18c0f4bc6b5c522f`.
Installed CLI SHA256: `cdb1fdb92390059ca55f076779e2f1b9323064540109c5ef791e651fdd74a5ca`.
The public library is shared; private bundled lrs/cdd implementation targets
are static/PIC. Earlier static r10 is separate evidence, not reused here.

Rule12 workflow: execute this package's installed bin/sympol twice with a
private UTF-8 path containing spaces. Convert a square's V representation to
all four exact rational facets, serialize those facets to disk, then recover
the original four vertices from H representation. Compare exact Fraction sets,
not output length, timing or an unconditional success string. Each subprocess
has a 60-second bound; absent package, nonzero exit, malformed/truncated data,
wrong count/dimension, incorrect facets or changed vertices fail the test.
L1e removes package bin/lib/include and confirms a genuine test failure.

Total original tests remain30. Added cases are2, not5: the original API
consumer's four assertions are one case, plus the one complete CLI workflow.
This counting correction removes no original assertion or upstream test.
