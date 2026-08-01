# openjpeg2 2.5.4 Path C Candidate Evidence

## Candidate scope

This document requests Path C candidate review only. It does not claim a Path
C score, final acceptance, package publication, or complete OpenHarmony runtime
coverage. The existing PR remains eligible for normal Path A review if the
candidate is not accepted.

The first package deliberately exposes the core `libopenjp2` library. It
disables codec command-line tools, JPIP, viewer, Java bindings, bundled
third-party helpers, documentation, and upstream test builds. A successful
core-library package must not be interpreted as evidence for those excluded
surfaces.

## Why candidate review is requested

OpenJPEG implements the JPEG 2000 codec API and supports a wider feature
closure than the core library package: encoder and decoder tools, JPIP
client/server code, optional image-format helpers, and data-driven conformance
and non-regression suites. Correctness involves codec behavior and sample/data
coverage, not merely linking a library. The candidate request is limited to
assessing whether that implementation and test surface justify Path C review.

## Actual test evidence

- PR #3396 CI build #11088 reported `conan test_package`, L0 structure checks,
  and L1 test-execution verification as passed. This is evidence that the
  packaged consumer executable was built and run by CI.
- The installed consumer is one C executable with six checks: version query,
  default encoder parameters, image creation, component count, component
  dimensions, and J2K compressor creation/destruction. It exercises public
  `libopenjp2` API use only.
- The recipe sets `BUILD_TESTING=OFF`, `BUILD_UNIT_TESTS=OFF`, and
  `BUILD_CODEC=OFF`. Therefore no upstream CTest entry was built or run by the
  package CI. The documented 33 basic CTest entries and the additional
  conformance/non-regression data-driven cases have no pass result here.
- This audit did not add a new native upstream result. Two bounded downloads of
  the official source archive for a local CTest rerun were interrupted by a
  connection reset and then a timeout. Those blocked attempts are not counted
  as test execution or as failures of OpenJPEG itself.

## Explicit boundary

The current evidence does not cover OpenHarmony execution of upstream CTest,
conformance, or non-regression datasets; codec CLI behavior; JPIP; viewer or
Java bindings; optional image-format helpers; or performance, fuzzing, and
security regression testing. It also does not claim that unavailable datasets
or disabled targets passed.

## Evidence required before completion

1. Enable and execute the intended upstream CTest scope in a reproducible
   environment, retaining actual PASS/SKIP/XFAIL/FAIL totals and identifying
   which data-driven datasets were available.
2. Retain the target-side Conan consumer execution log for the installed
   package, then extend it only with real codec round-trip or decode evidence
   when the required input/output boundary is available.
3. Treat each re-enabled optional feature family as separate evidence: codec
   tools, JPIP, bindings/viewer, and external image helpers must not inherit
   the core library result.

## External tracking

No Path C candidate Issue is linked yet because this audit had no authenticated
GitCode session for creating or updating external records. Once available, the
Issue should link PR #3396 and this document, retain the candidate-only scope,
and ask reviewers to confirm the required target-side test evidence.
