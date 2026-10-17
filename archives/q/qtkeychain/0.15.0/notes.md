# qtkeychain 0.15.0 notes

## Scope

This package provides the Qt6Keychain CMake package and `qt6keychain` target
needed by `ruqola` (QKeychain password/secret storage).

## Adaptations

- `BUILD_WITH_QT6=ON` builds the Qt 6 library variant.
- `BUILD_TESTING=ON` builds and runs the upstream autotest (`autotest/basic.cpp`,
  registered via ECMAddTests).
- `BUILD_TEST_APPLICATION=ON` keeps the upstream `testclient` application
  building as a compile/link smoke test.
- `BUILD_TRANSLATIONS=OFF` avoids a mandatory Qt LinguistTools lookup.
- libsecret support was removed upstream in 0.15.0, so no host libsecret
  dependency is needed.
- The recipe exposes the packaged Qt6 and ECM CMake module paths explicitly
  because upstream includes ECM modules directly.
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` is set because CMake has no
  Platform/HarmonyOS module (L5 gate: DT_SONAME present).
- Installed OHOS ELF files are re-signed after CMake installation.

## Verification

- Source archive SHA256:
  `f4254dc8f0933b06d90672d683eab08ef770acd8336e44dfa030ce041dc2ca22`.
- OHOS aarch64 `conan create` to be confirmed by conan-verify.
- The upstream `testclient` application builds successfully.
- The Conan `test_package` finds `Qt6Keychain`, links a CMake consumer and
  verifies QKeychain fallback store/read/delete.
---

**编译结束**: 2026-10-17 14:30
**最终状态**: built
