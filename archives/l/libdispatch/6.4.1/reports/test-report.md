# libdispatch 6.4.1 initial native Conan validation (historical)

This record describes the original PR candidate before CI91435. The source
layout changed during its subsequent CI repair; the new authoritative formal
and finish results are in source-layout-ci-repair.md. Old hashes below remain
the actual historical hashes, not substituted with new run hashes.

2026-10-14, Asia/Shanghai. Task 15204; branch upgrade/libdispatch-6.4.1.
The user explicitly selected path B on 2026-10-14 after the actual evidence
did not establish a C-class barrier. No Issue/PR or CI/release has occurred.

## Formal build and tests

Endpoint 10.62.210.132:2222, boot 2488bc3f-f5fe-4b70-b131-07c630c7157b,
UID 20020084. Native OHOS 6.0/armv8/Clang15/libc++/Release, Conan2.29.1.
Run libdispatch-conan-w3-20261014-r1, unique launch PID57486/start159519923.
Both modes use Conan create from downloaded, hash-checked official source,
the generated 15 source patches, and a task-private Conan home.

| Mode | Upstream registered/executed/passed | Installed public API consumer | Result |
| --- | --- | --- | --- |
| shared | 37/37/37 | 1/1 | PASS |
| static | 37/37/37 | 1/1 | PASS |

Shared/static repeats validate two linkage modes; they are not 74 independent
upstream tests or two different consumer test cases. The consumer has 12
runtime assert sites plus an OHOS 64-bit compile-time ABI assertion.

Consumer coverage: Blocks callbacks, queue/group sum55, one-time invocation,
64-bit callback context and atomic count, monotonic timer completion, and
dispatch data mapping. It includes only installed public headers and links
the installed package through generated CMakeDeps/VirtualRunEnv. OHOS ELFs
are signed by the recipe/test_package, not injected by the outside runner.

Full native extended C/C++ suite is enabled, including upstream's normally
default-OFF extended tests. Swift overlay remains off; Apple-only tests are
not registered by upstream on this platform. No registered test is excluded
or skipped. Inventory and JUnit ID sets were independently compared for both
modes; all 37 unique IDs match, with no failure/error/skipped elements.

## Important test modifications and limitations

- Release test fixtures retain assertions with tests-only -UNDEBUG; production
  optimization/assertion settings are not globally changed.
- Numeric casts resolve bounded test-metric conversions, without broad Wno-error.
- Concurrent queue fixtures use current private width API semantics; no hierarchy
  combination or functional assertion was removed.
- readsync binds its rendezvous worker count to actual internal pool capacity,
  retaining LAPS and mutual-exclusion assertions. This does not prove 1280
  workers can simultaneously execute.
- Test temporary files respect checked TMPDIR paths; no shared /tmp writes.
- Performance tests explicitly use upstream LENIENT_DEADLINES CI mode. The
  previous strict starfish <1000ns threshold failed at about1102-1282ns; this
  failure remains preserved and is not retroactively reclassified as PASS.

## Dependency and artifact identity

Core uses bundled BlocksRuntime and system interfaces. Only the extended
dispatch_io test needs published musl-fts/1.2.7. It is declared as test_requires,
not a delivered runtime requirement. Its immutable package files were checked
before execution; only a private build-folder copy of the library was signed.

Dependency RREV 5a8e6f41b363de99ed8c81f5c77d488e,
PID 01d92cf349a0dd98ff915f4bd99a04430171517f,
PREV 66a3f1b6a9f342f8af613342c1a4a5d3.

Created recipe RREV: 6111b2913080ba878258d697e324b375.

- shared PID 01d92cf349a0dd98ff915f4bd99a04430171517f,
  PREV 87fa39dd578d0dadf31ce5774f425fd6.
- static PID 21b17f8b2bc0e9511e276e3d57a23893067cefe5,
  PREV d831a44880dcf6106f64b0b962ac1d09.

Readonly artifact audit confirms two signed AArch64 shared libraries with
basename SONAMEs, no path-bearing NEEDED and no private build/cache RPATH.
libdispatch.so retains upstream $ORIGIN; libc++_shared.so is the system SDK
runtime. Static package contains only the two expected .a libraries and no .so.

All12 transaction receipts, release/postrelease and independent exact-byte
collection passed. Log SHA-256:
41fdf8b428ec0b95e83504db9747b9fadd2a01a6c4df2b57cd249243815d270a.

Task-local evidence: libdispatch-conan-w3-20261014-r1/collected-* and
dispatch641-package-audit.json under the adaptation root. Native baselines
and failed attempts remain separate historical records.

## Complete native finish

`libdispatch-finish-w3-20261014-r5` completed the actual finish command with RC0.
ConanVerifier and the actual CI setup/build scripts each executed upstream37/37
and public installed consumer1/1. W5 completeness, archive finalization, W2
atomicity and current Conan readiness all passed. One historical notes-format
warning is nonblocking. All12 immutable receipts include release/postrelease;
runner exited, launch_count1. This is not a contest-worker CI result.

Aggregate finish log SHA256:
`40ec242581a81aa6dc217bf5095f3fef56b684ff979a9b492cbf190520dd705e`.
Actual local-CI log SHA256:
`def26e092387bfa2c481955cd0f445ea8d1692b951cb5478728dfdb07ae587ea`.
The producer-generated CI result integrity479e95b8422b2d43 and exact log hash
were independently recomputed. No result marker was manually created or edited.
The earlier RC1 attempts remain failed transactions, not promoted to PASS.

The task-private runtime projected canonical LF recipe inputs and separately
bound the host base HEAD/tree. It is not claimed to clone the full host Git tree.
Before the subsequent CI repair, final candidate changes after this run were reports/task readback/knowledge
metadata only; runtime recipe, test source and patch bytes are unchanged modulo
the already declared CRLF-to-LF projection. Framework fixes stay in a separate
worktree and are not part of this software PR.

## Submission boundary

Knowledge dedup and supported negative HD1–HD4 reassessment are complete.
Issue/PR association and PRE_CREATE/POST_CREATE are handled in the submission
checkpoint. Platform AI Review and worker CI are not claimed passed here;
publication happens only after merge.
