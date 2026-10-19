# SGA 0.10.15 — native data-path validation

Date: 2026-10-15. Target: OHOS 6.0, arm64, Clang 15, C++17, one build job.
This report is not a platform CI/publication certificate. Official native
Conan verification and W3 passed in sga-ci-fix-210-20261015-r6 (12 receipts,
released). Official W3 log SHA256:
66932b5b0ceac2acbc5104fa65bdb1396f05460e4fcd8fbdfd9d8c54b8cece29.
Aggregate finish remains PARTIAL_POST_W3 RC1 (step5b,step8), not full finish
PASS. Independent W5 and Pre-PR contracts govern their respective readiness.

The current recipe declares Autoconf, Automake and Perl as build tools; m4 is
published in the tool closure. Toolchain activation puts the declared Perl
before the profile PATH so Automake's bare-perl wrapper cannot load mismatched
XS modules. AUTOM4TE is one wrapper pathname, as required by autoheader.
Tested tree: 42ba9b40f230eb77e80c6854b1674981e0227984.
Current installed CLI SHA256:
b729a24faedc9e898ba4ccb400f016868e67a2641c5b6bd73b4047933afb651e.
Official L0/L1/L2/L4/L5 and destructive consumer negative passed. Earlier
failed wrapper transactions remain FAIL; none are relabeled or spliced here.

Upstream has no registered TESTS/check_PROGRAMS suite in this release (0/0).
Dockerfile.testing builds the project but does not define a test suite. The
following checks are supplemental and are not counted as upstream cases.

| Scope | Result |
| --- | ---: |
| CLI version, SAIS/ropebwt indexes, exact inverse-BWT multiset roundtrips, invalid-command rejection | 6/6 |
| Installed ropebwt index and exact roundtrip using UTF-8 paths | 2/2 |

Exact roundtrips preserve duplicate sequence multiplicities. Both index
algorithms use actual data; help/version alone are not functional substitutes.
No earlier help-only run is accepted as data-path validation.

## Historical parser-fix verification (not the current tool-closure run)

Frozen run: sga-w3-20261014-r13. Candidate tree:
`575aba84650b96a67362c9800c9d28fb2374f69e`.
Native Conan create returned zero. Full 12-receipt validator returned W3_PASS
after release, with no owned child process remaining.
Log SHA256: `3078c14b1ccc86f4b28a3e22dedcc8d770c044563f34c88878e45cb9889fff64`.
Installed CLI SHA256: `3e54f0920784b38d44c73f72bd5918089e89e26ee1aef6f72014e64137d5112e`.
All 32 getopt_long result receivers now retain int and its -1 sentinel.
