# palabos 2.3.01 adaptation notes

## Build environment
- Build system: cmake (root CMakeLists.txt, static library, no install rules)
- Adaptation date: 2026-10-14
- Compiler: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- Status: built (pending real-device preflight)

## Build steps
1. `get()` official GitLab archive v2.3.0 (task version 2.3.01 maps to upstream v2.3.0 content).
2. CMake configure with `-DCI=OFF -DENABLE_MPI=OFF -DENABLE_POSIX=ON -DBUILD_SHARED_LIBS=OFF`.
3. `cmake --build` produces `libpalabos.a` in the build tree.
4. `package()` copies `libpalabos.a` to `lib/` and `src/*.h/*.hh` plus
   `externalLibraries/{tinyxml,Eigen,Eigen3,nanoflann,sitmo}` headers to `include/`.
5. Upstream has no test suite, so `build()` emits a `no_tests` HMBS marker after audit.

## Dependency analysis
| # | Dependency | Result | Evidence |
|---|------------|--------|----------|
| 1 | MPI | Not required, disabled | `option(ENABLE_MPI)` set OFF; no MPI on OHOS |
| 2 | External libs | Vendored | `externalLibraries/` ships Eigen/tinyxml/nanoflann/sitmo in-tree |

No `requires()` entries; no prebuilt dependency lookup needed.

## Source modifications
No static patches. `build()` runs `_gate_examples()`, which comments out
every `add_subdirectory(examples/...)` / `add_subdirectory(utility/...)`
line in the upstream root CMakeLists.txt (line-oriented, ~80 entries:
1 benchmark + 27 codesByTopic + 27 showCases + 3 tutorial + 19 stl + 2 vtk).
This replaces the Round-3 static patch 0001, which failed to apply on the
device (`source file is different` at
`examples/showCases/particlesInCone`) due to wrong hunk line numbers
(second hunk `@@ -150,2` does not match the real v2.3.0 file).
Round 5 adds `_fix_cxx17_random_shuffle()` for the C++17
`random_shuffle` removal (`metaStuffWrapper3D.cpp:85`); programmatic,
no static patch.

## Reference versions
No prior palabos archive in this repo; first adaptation.

## Verification
Pending HMBS real-device preflight (`conan create` on HarmonyOS aarch64).
Expected:
- `HMBS_UPSTREAM_TEST_RESULT` with `status:"no_tests"`, discovered/executed 0.
- `HMBS_TEST_PACKAGE_RESULT` with discovered 4 / passedCount 4 from `./test_palabos`.

## Preflight history
- Round 1 (2026-10-14): `cmake.configure()` failed at root `CMakeLists.txt:1`
  (`cmake_minimum_required` < 3.5 rejected by device CMake 4.4.3). Fixed by
  injecting `CMAKE_POLICY_VERSION_MINIMUM=3.5` via `tc.cache_variables`.
- Round 2 (2026-10-14): configure progressed to `CMakeLists.txt:9 project()`
  but both C and CXX compiler checks failed for
  `/data/service/hnp/bin/clang/clang++` with `System is unknown to cmake /
  Platform/HarmonyOS`. Same signature as mathic/1.4 rounds 2-8: that track
  proved E191 bypass ineffective and E557 host-runtime recovery a no-op, and
  the toolchain probe finally proved both profile compiler paths stat ENOENT
  on current preflight workers (device migrated clang to `~/usr/local/bin`,
  profile still points at the old path). Fix follows the zydis/4.1.1-validated
  compiler-migration pattern (no E191 bypass, no test skipping): main recipe
  and test_package each resolve the real compiler (configured path if it
  exists, else PATH `which`, else `~/usr/local/bin` fallback), pin it via
  `tc.cache_variables["CMAKE_C/CXX_COMPILER"]`, rewrite any stale absolute
  path left in the generated `conan_toolchain.cmake`, export build-scope
  CC/CXX, persist a writable TMPDIR for try_compile, and print
  `HMBS diag` lines so the next preflight log carries ground truth.
- Round 3 (2026-10-15): compiler migration worked (diag resolved
  `.harmonybrew/bin/clang`, toolchain rewritten, `Clang.`/`Enabling POSIX`
  printed), but configure failed in the examples phase: every example
  subdir early-returns under `if(CI)` (root-tree mode, builds only its own
  demo exe) and otherwise falls into a standalone section that re-runs
  `add_library(palabos ...)`. The recipe's `CI=OFF` therefore duplicated
  the palabos target ~60 times, plus duplicate `cavity3d` exe targets and
  a hard `find_package(HDF5 REQUIRED)` failure in
  aneurysm_xdmf_hdf5_output (CI=ON would still fail there and would build
  60+ exes). First fix attempt (static patch 0001 gating the block on
  PALABOS_BUILD_EXAMPLES) failed to apply on the device; see Round 4.
- Round 4 (2026-10-15): the Round-3 static patch 0001 failed in
  `apply_conandata_patches` on the device (`source file is different` at
  `add_subdirectory(examples/showCases/particlesInCone)`). Root cause was
  brittle hunk headers generated against an assumed line layout (second
  hunk `@@ -150,2 +151,3 @@` does not match the real v2.3.0
  CMakeLists.txt fetched from
  `https://gitlab.com/unigespc/palabos/-/raw/v2.3.0/CMakeLists.txt`).
  Fix: drop the static patch and `conandata.yml` patches stanza; `build()`
  now runs `_gate_examples()`, which comments out every
  `add_subdirectory(examples|utility ...)` line programmatically
  (raises if zero found, logs the gated count). No `__OHOS__` macros, no
  test-scope change. Only the `palabos` static library is built. Examples
  are demo-only compiles; upstream has no tests, so the test scope is
  unchanged.

## Artifacts
| File | Size | Note |
|------|------|------|
| libpalabos.a | TBD after preflight | Static LBM library |
| include/palabos2D.h, palabos3D.h | vendored | Public entry headers |

## Notes
- Task version 2.3.01 has no matching upstream tag; upstream latest is v2.3.0
  (commit bba6dc64, 2021-06-05). The recipe uses the official v2.3.0 archive
  and keeps the task version string for the Conan package.
- Root CMake forces `-std=c++11`; left as-is (clang 15 accepts it).
- `build()` gates out the 60+ demo examples on the memory-constrained
  device job (jobs=1) via `_gate_examples()`; upstream `CI`
  semantics are inverted (CI=ON means root-tree mode), so CI is left at its
  default and no longer overridden.
- Round 5 (2026-10-15): preflight compiled to 34-35% then failed in
  `src/dataProcessors/metaStuffWrapper3D.cpp:85` with
  `error: no member named 'random_shuffle' in namespace 'std'`
  (`std::random_shuffle(ids.begin(), ids.end())`). Root cause is a C++17
  API removal (random_shuffle deprecated in C++14, removed in C++17);
  the device clang defaults to C++17 while upstream v2.3.0 (2021) still
  uses the old call. Fix: `build()` now runs `_fix_cxx17_random_shuffle()`
  before `_gate_examples()`; it scans all .cpp/.h/.hh/.hpp under the
  source tree, inserts `#include <random>` where missing, and rewrites
  the 2-arg `std::random_shuffle(a, b)` into
  `std::shuffle(a, b, std::mt19937{std::random_device{}()})` via a
  balanced-paren scan (regex `(.*?)` fails because args contain parens;
  3-arg form is left untouched). `std::shuffle` exists since C++11 so the
  result still builds under C++11. No test-scope change.
- Round 6 (2026-10-15): main library reached `[100%] Built target palabos`
  after the Round-5 shuffle fix, but test_package failed at
  `test_palabos.cpp:36` with
  `error: use of class template 'D2Q9Descriptor' requires template arguments`
  (`template <typename T> struct D2Q9Descriptor`). Root cause is a test-only
  authoring error: `D2Q9Descriptor` is a class template, so `DESCRIPTOR::q`
  is ill-formed; lattice/BGK call sites correctly pass the template itself
  (`MultiBlockLattice2D<T, DESCRIPTOR>`, `BGKdynamics<T, DESCRIPTOR>`).
  Fix: check 1 now reads `DESCRIPTOR<T>::q == 9`. No library change,
  no assertion removed, still 4 checks.
- Applicant: zhangyuge147, team: long-knight (Long Knight).

- Round 7 (2026-10-16): CI build 93575 failed cmake compiler self-check with /bin/sh: cant fork - try again AFTER Clang 15.0.4 identification passed, at TryCompile-aFaCBC via Unix Makefiles (SHELL=/bin/sh). Different strategy from prior no-change round: main recipe and test_package now probe for a real ninja binary (HMBS_NINJA, user.hmbs:ninja_path, PATH) and use CMakeToolchain(generator=Ninja) on OHOS only when found, else keep Makefiles; choice logged as HMBS diag generator. Rationale follows aws-lc-tools/5.2.0 OHOS precedent. No test-scope change; package() walks build tree so generator-agnostic.

- Round 8 (2026-10-16): CI build 94047 proved Round 7 Ninja switch works for configure (reached CMake.build()), then failed at cmake --build ... -- -j20 with ninja: fatal: posix_spawn: Resource temporarily unavailable. Root cause is Conan default parallelism fanning out 20 clang processes on the shared worker. Fix: cmake.build(build_tool_args=[-j1]) in main recipe and test_package (zarchive/0.1.2 precedent, repo R9 always -j1). No test-scope change.

- Round 9 (2026-10-16): CI build 94119 (CI-030) moved past compile [1/2] under Ninja but failed the TryCompile link [2/2] (`: && clang ... && :` via /bin/sh) with /bin/sh: can't fork, while the same code passed TryCompile on CI-001 (#94047 reached build). Fix: set CMAKE_C/CXX_COMPILER_WORKS=1 plus CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY via tc.cache_variables in main and test_package (extra-cmake-modules/6.28.0 + cryptokit/1.21.1 precedent; compiler proven by Clang 15.0.4 identification and preflight full-lib build). Upstream root CMake needs no ABI/run checks, so skipping the redundant self-check is safe. No test-scope change; prior -j1 serialization retained.
