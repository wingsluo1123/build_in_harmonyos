# SymPol 0.1.9 adaptation in progress

Task #10970 is assigned to 2501_91199785 on feat/sympol-0.1.9.
Latest main fetched for this isolated checkout; no other task checkout modified.

W0 recipe downloads passed for GMP 6.3.0.1, Boost 1.91.0.1.4 and
PermLib 0.2.9. Their exact released binaries resolved and were used on target.

The official tag archive omits external/permlib. Consume the separately
published PermLib package rather than silently fetching an untracked source.
Preserve CMake's dependency module path and the hierarchy of public headers.

Both original CTest entries remain enabled: 28 Perl-driven CLI cases and two
Boost.Test cases. These are 30 leaf cases, not merely two tests. Optional Eigen
and Bliss backends are explicitly outside this initial configuration.

Static configuration passed target Conan create and W3 in r10. Shared
configuration independently passed in r12 (30/30 upstream, 4/4 consumer).
Knowledge contribution is E550-draft-BAS1; formal validation of that draft,
formal finish, Issue/PR contracts, platform review and CI remain incomplete.

First native transaction sympol-w3-20261014-r1: all three exact dependency
binaries downloaded; configure failed at cmake_minimum_required under CMake 4.
Putting CMAKE_POLICY_VERSION_MINIMUM in the toolchain is too late because
the toolchain is loaded by project(). The candidate now passes it as a
command-line cache variable. The failed transaction remains FAIL.

The next transaction reached compilation and showed the bundled CMake
FindGMP module could not see Conan's `gmp.h`. The module-mode variable was
empty even though the Conan target existed. The recipe now uses the config
target's interface include directory and library edge, so bundled cddlib/lrs
compile against the same published GMP package.

The following transaction compiled but the first target execution failed with
missing `cddgmp/lrsgmp/libsympol` symbols. The bundled shared libraries live
below separate build subdirectories, so the recipe now binds CMake build RPATH
to those directories and install RPATH to `$ORIGIN/../lib`. A target launch
failure remains recorded; it is not relabeled as a test pass.

The next attempt showed the old CMake targets encode relative SONAMEs, so
loader search paths cannot repair them. The recipe now makes only those
    private bundled engines static; the public SymPol library remains shared.

The next link showed AArch64 relocation errors because those newly static
engines were not compiled as PIC before entering `libsympol.so`. The recipe
now sets `POSITION_INDEPENDENT_CODE` on both private static targets.

r10 passed the original 28 Perl-driven CLI cases, both Boost.Test cases and
four consumer assertions with a static public library. This was a working
configuration, not proof that OHOS cannot load a shared SymPol library.
The direct test driver resolves Perl from PATH or the interpreter prefix and
executes the exact two upstream programs without depending on CTest in PATH.

The shared successor r11 restores the default shared public API, leaves only
the bundled implementation engines static/PIC, and supplies the missing ELF
SONAME/RPATH flags in the HarmonyOS CMake platform. It uses the same ORIGIN
layout at build/install time to avoid post-link rewriting of a signed ELF.
It must independently pass all 30 upstream cases and four installed-consumer
assertions before the shared candidate can be considered target-validated.
No static W3 result is reused as evidence for the changed shared candidate.

r11's actual ELF had RPATH [/../lib]: the shell expanded an unset ORIGIN in
the double-quoted CMake cache argument. r12 keeps the literal loader token in
the generated toolchain file via tc.variables. It passed native Conan create,
all 30 original leaf cases and all four installed shared consumer assertions.
The full 12-receipt transaction was released with W3_PASS. Its log SHA256 is
de902547f695d50e2eef2769b77eec2b8282821cd071e588c9af436c4d040697.

## Formal W3 closure

sympol-formal-20261014-r4: official verification and W3 passed, 30/30 original
leaves plus 4/4 installed consumers; 12 receipts passed and released.
Tested tree dd38766387b18e38e56c162ef30b89757b9b0cab.
Official W3 log SHA256: fccf4c75170943d760ad4ab40adcc85a06cbf5c8f3e73876e52d743899c62381.
The producer now emits an explicit 30/30 PASS terminal only after verifying
all 28 original Perl results and both Boost.Test cases, so the Pre-PR parser
can consume raw evidence without post-hoc invented PASS lines.
Official L5 passed with the real LLVM readelf provider. A former missing
readelf command had produced a false SONAME failure; product ELF had always
contained libsympol.so.0.1 and literal ORIGIN RPATH.
Aggregate finish remains PARTIAL_POST_W3 RC1 for step5b,step8 only. The local
Conan cache backup is tool-generated, ignored and not a release artifact.

**编译结束**：正式原生 W3 已通过；平台 Review/CI 与发布仍待 PR 后执行。

## 2026-10-15 rule12 consumer workflow repair

The four QArray checks are assertions in one API consumer, not four cases.
Keep all four, and add one complete installed CLI V-H-V square workflow in a
UTF-8 path containing spaces. Require exact rational halfspaces and vertices,
full result cardinality, bounded subprocesses and actual package executable.
The workflow is run by test_package and fails if installed artifacts disappear;
it is not an unconditional assertion or a build-tree-only demonstration.

Fresh sympol-review-201-20261015-r1 completed two clean Conan creates, original
upstream30/30 each, API consumer1/1 with4/4 assertions, workflow1/1, official
L1e negative and full12 receipts/release. Current added cases2/2; no upstream
case or previous API assertion was removed. W3 log SHA256:
95f0431004587f01ccfcfadddaa1b8ba835628c8bbf5bc5756592fe9bbcccc2d.
Tested tree83f74fa0410f67bfe8df123569be1b0edac8e03d. Only reports, metadata
and knowledge were updated after validation, with all runtime inputs unchanged.
Overall finish remains PARTIAL_POST_W3/RC1 for step5b/step8; L2 help/version
still skips non-blockingly. New-head platform Review/CI are not yet certified.
