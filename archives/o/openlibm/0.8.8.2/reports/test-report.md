# openlibm/0.8.8.2 target test report

## Scope

- Source: official `v0.8.8`, SHA-256 `721bab18ff37160fd9e903eb211ff26fdee38c3d0041d556b07d76089c435d17`.
- Target: authorized OHOS AArch64 device, clang 15, Conan 2, CMake, Release, at most two build jobs.
- Private validation of the downstream `0.8.8.2` recipe. This report does not claim remote CI success.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Conan create / CMake static library | PASS, `[100%] Built target openlibm` | Private `target-native-a009/create.log`, SHA-256 `361b5c3453806ba6f61cfb124771ac8300c4670a1015e5d0dba5255477ab5c4c` |
| Package artifact readback | PASS, archive, public header, pkg-config version `0.8.8.2`, byte-identical upstream license | Private `target-native-a009/package-readback.json`, SHA-256 `7b023752c151a6b39b7b79e157c9f265eb7dce7204b20bc6eb06600de90dcfac` |
| Official upstream `make test` | PASS, 4,075/4,075 assertions, 0 failures; 3 architecture-gated skips | Private `target-native-a009/upstream-test-a010.log`, SHA-256 `bb051a013b4f9d87b50e9f9098cf3fcb2721228603ae6d6db16411600f31353b` |
| Installed Conan consumer | PASS, 13/13 numerical, ld128 and fenv checks; `OPENLIBM_INSTALLED_CONSUMER_PASS` | Private `target-native-a009/consumer13-a011.log`, SHA-256 `f1aceafd31d7441beb5cb4ee810a1c1266f8b42d3354d53618038b292e9d411e` |

Upstream assertion breakdown: `test-double` 1,118 values + 932 exception checks = 2,050; `test-float` 1,101 values + 923 exception checks = 2,024; regression `test-211` = 1. Regression `test-222`, `test-252` and `test-334` exit with upstream architecture-gated skip status on AArch64. Adding the 13 installed-consumer checks yields 4,088 executed passing assertions across both runs.

## Failure analysis retained

- a007 patch context was malformed and rejected before build; corrected patch hunk length.
- a008 built the library, then the package assertion correctly rejected `openlibm.pc Version: 0.8.0`. Passing the version via CMake toolchain was too late for upstream's pre-`project()` read. Passing it on the configure command line fixed a009.
- The first upstream test invocation could not make a temporary linker file because the default temp location on the device was read-only. The independent a010 invocation set a writable private `TMPDIR` and completed the full suite.

Private raw logs and readback receipts are held in `D:\MY_FILE\HarmonyPC-New-PC-Adaptation-Kit-20260828\new-pc-adaptation-kit-20260828-r1\workspace\openlibm-probe\target-native-a009\`.
