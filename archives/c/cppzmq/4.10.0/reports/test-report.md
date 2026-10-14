# Test Report — cppzmq 4.10.0

## Environment

- OpenHarmony / HarmonyOS PC, aarch64 (real device / local machine)
- Clang 15.0.4 (OHOS SDK `ohos-sdk_26.0.0.18` LLVM; native `aarch64` / `musl` ELF output)
- Conan 2.29.1
- Profile: `ohos-aarch64` (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15, libcxx=libc++, cppstd=17, build_type=Release)
- Package type: **header-only** C++ library (`package_type=header-library`) — no `.so`/`.a` artifacts

## Verification

- `conan create` (run by the local CI simulation): **PASS** — package built and both
  test_package executables built and executed.
  - log: `archives/c/cppzmq/4.10.0/reports/conan-create.log`
  - evidence: `[100%] Built target test_cppzmq`, `[100%] Built target test_cppzmq_ohos`,
    `cppzmq test passed! All assertions OK.`, `OHOS consumer test PASSED (cppzmq + zeromq on OpenHarmony aarch64)`
- `CI_PACKAGES="archives/c/cppzmq/4.10.0" zsh ci/conan/build_and_test.sh`: **exit 0**
  (W3 local CI simulation passed; identical script + profile as remote CI)
  - log: `archives/c/cppzmq/4.10.0/reports/w3-local-ci.log`
  - gate results: `G0=pass, KC=pass, JC=pass, L0=pass, L1=pass, L2=skip (no bin/), L4=pass, L5=pass`
  - `Success: 1  Failed: 0  Pass rate: 100.0%`
- `conan-verify cppzmq 4.10.0` (R29 recipe verification): **PASS** — all gates green
  (`G0/G1/G2/G3/G4/L2/L4/L5 = PASS`, verdict `PASS`).
  - report: `archives/c/cppzmq/4.10.0/reports/conan-verify-report.md`
  - note: this required an ELF-based `conan` launcher on the local machine — this device denies
    `execve` of shebang scripts from CPython-lineage processes (environmental sandbox property,
    not a package defect).
- Version-collision gate (R37 / L0j): `conanfile.py` and `conandata.yml` are byte-identical to
  the recipe already in the registry → **recipe unchanged**, therefore **no version-suffix bump is
  required** (this adaptation adds tests only; it does not modify the published recipe inputs).

## test_package (adapted)

Two executables are built and executed inside `conan create`:

### 1. `test_cppzmq` — assertion-based consumer test (5 assertions)

Exercises the cppzmq C++ wrapper API:
- creates `zmq::context_t` and validates the handle
- creates REQ/REP sockets over `inproc://`, sends and receives a message
- asserts payload round-trip equality
- tests `zmq_addon` multipart send/recv with 2 frames

**Result**: `cppzmq test passed! All assertions OK.` (exit 0)

`assert(` call count (measured): **5** — `test_cppzmq.cpp:10,28,35,39,40`

### 2. `test_cppzmq_ohos` — HarmonyOS-specific consumer test (assertion-free, rule12)

A HarmonyOS (OHOS aarch64) consumer test that substantively drives cppzmq + libzmq and is
**not assertion-based** (`assert()` call count = **0**; the only textual match is a comment on
`test_cppzmq_ohos.cpp:11`). Failure is reported via explicit boolean checks accumulated in
`g_failures` and a **non-zero process exit code** (0 = pass, 1 = check failure, 2 = exception).

Business closed loop (construct input → call the library API → produce result → validate content):
- creates `zmq::context_t`
- real inproc REQ/REP round trip: REQ `send` → REP `recv` → REP `send` reply → REQ `recv`
- multipart encode/decode over a PAIR socket via `zmq::send_multipart` / `zmq::recv_multipart`
  with per-frame content validation

**Result**: 11 `OK:` lines then `OHOS consumer test PASSED (cppzmq + zeromq on OpenHarmony aarch64)` (exit 0)

### Test summary

| Metric | Value |
|--------|-------|
| Test executables | 2 |
| Test cases executed | 2 |
| Passed | 2 |
| Failed | 0 |
| Skipped | 0 |
| Assertions (`test_cppzmq`) | 5 |
| Assertions (`test_cppzmq_ohos`) | 0 (assertion-free by design) |

## Upstream tests (Catch2 suite)

The upstream repository ships a **Catch2** test suite (`tests/*.cpp`, Catch2 v2.13.9 fetched via
CMake `FetchContent`), totalling **102 test cases**.

Because the package is header-only, the conan recipe intentionally keeps
`-DCPPZMQ_BUILD_TESTS=OFF` (there is nothing to compile in the recipe build). The upstream suite was
therefore built and executed in a **separate, out-of-recipe CMake build** with
`-DCPPZMQ_BUILD_TESTS=ON`, using the same OHOS toolchain, and is reported separately:

- build: `cmake -DCPPZMQ_BUILD_TESTS=ON ..` (FetchContent fetches Catch2 v2.13.9)
- run environment: OHOS aarch64 (native clang 15.0.4; `unit_tests` is an `aarch64` / `ld-musl-aarch64.so.1` ELF)
- result: `100% tests passed, 0 tests failed out of 102` (**102 passed / 0 failed / 0 skipped**)
- evidence: `archives/c/cppzmq/4.10.0/reports/upstream-ctest.log`
  (supporting toolchain evidence: `reports/upstream-build-cache.txt`)

| Metric | Value |
|--------|-------|
| Upstream test cases | 102 |
| Passed | 102 |
| Failed | 0 |
| Skipped | 0 |
| Pass rate | 100% |

## W4 Pre-PR Audit

- `reports/audit-result.json`: `verdict = pass`, P0 = 0, P1 = 0
  (1 × P2 evidence-traceability note, 2 × P3 suggestions — none blocking)
