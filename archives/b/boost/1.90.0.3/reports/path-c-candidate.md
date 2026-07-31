# Boost 1.90.0.3 Path C Candidate Evidence

## Application Boundary

This document requests Path C candidate assessment for the compiled-component
Boost 1.90.0.3 archive. It does not claim a Path C score or final acceptance.
The archive remains subject to the normal review, local upstream-test, CI, and
target-runtime requirements.

## Why This Is A High-Difficulty Candidate

1. **Large, multi-component ABI surface**: the selected package exposes the
   Boost headers plus atomic, chrono, filesystem, program_options, regex,
   serialization, thread, and timer. These libraries have inter-component
   dependencies and C++ ABI, threading, filesystem, parsing, and serialization
   behavior that cannot be established by a header-only check.
2. **Native Boost.Build toolchain integration**: Boost's `b2` build system
   does not consume a CMake toolchain directly. The OpenHarmony path generates
   a dedicated `user-config.jam` and compiler wrapper so an implicit Linux
   target triple cannot replace the configured OpenHarmony target.
3. **Downstream dependency closure**: FastNetMon needs the compiled Boost
   components and uses the adaptation suffix `1.90.0.3` because the repository
   already carries a header-only `boost/1.90.0`. A correct package must retain
   standard CMake component targets while avoiding a false `Boost::system`
   binary-library requirement for this upstream release.

## Implemented Adaptation Scope

- Builds the selected upstream components with Boost.Build and installs their
  headers, static or shared libraries, and CMake component metadata.
- Maps the OpenHarmony target architecture to the correct Clang target and
  filters only the conflicting target flags inserted by the generic Boost.Build
  toolset.
- Corrects two upstream test-harness defects needed to execute the selected
  component suites: Serialization names its Filesystem library target
  explicitly, and Regex examples no longer convert a negative
  `istream::in_avail()` result into an unsigned allocation size. Neither patch
  changes the packaged Boost library implementation.
- Preserves shared/static configuration, C++14 selection required by Boost
  1.90.0, and `-fPIC` for static non-Windows builds.
- Provides a consumer test covering program options, regex, filesystem,
  serialization, atomics, threading, timer, chrono, system error codes, and a
  header-only Beast type. Runtime execution is guarded with `can_run(self)`
  for cross builds.

## Actual Evidence And Boundaries

| Evidence | Actual result |
| --- | --- |
| Source integrity | `conandata.yml` lists official Boost release URLs and SHA256 `49551aff3b22cbc5c5a9ed3dbc92f0e23ea50a0f7325b0d198b705e8ee3fc305`. |
| Recipe/static checks | Recipe and test-package Python compilation plus `git diff --check` passed. |
| Upstream test harness patches | Both patches dry-run against the official source and were exercised by the complete local component run. |
| Consumer behavior | The local Conan consumer test compiled, linked and executed all 11 listed component assertions successfully (1/1). |
| Upstream Boost tests | Clean WSL/Linux x86_64 GCC 15.2.0 execution of the selected component test trees passed 1578/1578 Boost.Build targets. 76 expected compile-failure assertions were accepted by Boost.Build; no unexpected target failed. |
| OpenHarmony runtime | Cross-built target binaries must be executed on a runnable OpenHarmony target; host-side Linux execution is supplementary evidence only. |

## Proposed Acceptance Items

1. Build the same archive with the OpenHarmony profile and run the packaged
   consumer binary on a runnable target environment.
2. Confirm FastNetMon and other dependents resolve the published compiled
   component version without importing unrelated archive diffs.

## Review Questions

1. Does the Boost.Build/OpenHarmony toolchain bridge and downstream dependency
   closure meet the Path C candidate threshold?
2. Is the selected compiled component set sufficient for the declared first
   downstream scope, or should additional Boost libraries be split into a
   separate evidence set?
3. Which OpenHarmony target-side test evidence is required before the candidate
   can be considered complete?
