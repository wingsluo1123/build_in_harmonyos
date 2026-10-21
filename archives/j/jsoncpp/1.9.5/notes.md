# JsonCpp 1.9.5 OpenHarmony PC adaptation notes

## Scope

JsonCpp 1.9.5 adaptation for HarmonyOS PC (aarch64). JsonCpp has no
third-party dependencies of its own; this package is a CI-input recipe with
official GitHub source (R39).

## Source

- URL: https://github.com/open-source-parsers/jsoncpp/archive/refs/tags/1.9.5.tar.gz
- SHA-256: `f409856e5920c18d0c2fb85276e24ee607d2a09b5e7d5f0a371368903c275da2`
- Build system: CMake
- Offline validation: set `JSONCPP_SOURCE_ARCHIVE` to the same official
  tarball; the recipe verifies its SHA-256 before extraction.
- Independent re-download from codeload confirms the same SHA-256.

## Historical note (R15 纠错)

The 2026-05-21 archive for 1.9.5 only had `manifest.yaml` (status: published,
build_system: cmake) and `notes.md`; the manifest `source.url` pointed to a
local `file://` path (violates R39/PF7) and `sha256` was empty, so it was not
usable as-is. This adaptation rebuilds the complete recipe (conanfile.py +
conandata.yml + test_package/ + patches/) with the official source URL.

## Package design

The upstream defaults build shared, static, and object variants together.
The Conan recipe instead maps `shared=True` to only `libjsoncpp.so` and
`shared=False` to only `libjsoncpp.a`; `BUILD_OBJECT_LIBS` is always disabled.

For HarmonyOS, the recipe supplies CMake's missing SONAME and build-RPATH
linker variables. The source patch suppresses `VERSION` and `SOVERSION` only
when `CMAKE_SYSTEM_NAME` is `HarmonyOS`, avoiding HMDFS symlinks while keeping
a basename SONAME. Linux retains upstream versioned-library behavior.

HarmonyOS Python 3.12 raises `TypeError: can't concat str to bytes` while
the upstream `runjsontests.py` reads an `os.popen` text stream. The second
patch keeps the same commands and failure semantics, but captures bytes with
`subprocess.PIPE` and performs an explicit UTF-8 decode. No test is skipped.

## Test inventory (R51)

| Category | Cases | Evidence |
|---|---:|---|
| Unit fixtures | 121 | `JSONTEST_FIXTURE_LOCAL` registrations in `src/test_lib_json/main.cpp` |
| Parser/writer data inputs | 63 | `test/data/*.json` files |
| JSONChecker inputs | 27 | Runnable inputs after 9 upstream exclusions |
| Consumer unit | 1 | `test_package/unit.cpp` |
| Consumer integration | 1 | `test_package/integration.cpp` |
| HarmonyOS-specific | 1 | `test_package/ohos_portability.cpp` |

The `_WIN32`-guarded `StreamWriterTest/escapeTabCharacterWindows` fixture is
not registered on HarmonyOS and is excluded from the count.

Upstream total: 211 (121 + 63 + 27). New consumer flows: 3.

Note: JsonCpp 1.9.5 has no `Json::version()` runtime helper (added in 1.9.6+);
the portability consumer validates the `JSONCPP_VERSION_STRING` header macro
instead.

## Native HarmonyOS validation

Environment: HarmonyOS aarch64, Conan 2.29.1, CMake 4.1.2, Clang 15.0.4,
Python 3.12.9, profile `ci/conan/profiles/ohos-aarch64`.

- `conan-verify` (8 gates): PASS — G0/G1/G2 (conan create)/G3/G4/L2/L4/L5.
- Upstream CTest: `jsoncpp_readerwriter` (63 inputs, 10.7s),
  `jsoncpp_readerwriter_json_checker` (27 inputs, 13.7s),
  `jsoncpp_test` (121 fixtures, 0.04s) — 3/3 passed.
- test_package consumers: `jsoncpp_unit_consumer`,
  `jsoncpp_integration_consumer`, `jsoncpp_ohos_portability` — 3/3 passed
  after `binary-sign-tool` signing.
- W3 local CI (`ci/conan/build_and_test.sh`): JC/L0/L1/L4/L5 all pass,
  Success 1/1, Pass rate 100.0%; `.ci-result.json` exit_code=0 written by
  finish step [5/10].

## W3 junk_check note

The local W3 `junk_check` falls back to full-repository scan when there is no
diff against `origin/main`. Eight historical `.build-closed`/`.staging-verified`
files tracked on main under other packages (cloog/kics/libbfio/libdazzle/
oscpack/reflex/thc) trip JC1/JC5 in full mode. Committing the recipe on the
`feat/jsoncpp-1.9.5` branch switches junk_check to incremental mode (PR diff),
which only inspects this package's files.

## Evidence

- 上游: 211/211 (121 fixtures + 63 data + 27 JSONChecker)
- Consumers: 3/3
- conan create from clean cache: RC=0, package
  `jsoncpp/1.9.5@ohpcd/stable`.
- Artifacts: shared package `libjsoncpp.so` (SONAME basename, signed on
  OHOS), static package `libjsoncpp.a`.

---
**编译结束**: 2026-10-15
**最终状态**: built