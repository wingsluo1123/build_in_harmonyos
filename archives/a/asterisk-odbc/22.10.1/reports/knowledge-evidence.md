# Knowledge Evidence - asterisk-odbc 22.10.1

## Scope

This report supports the draft
`DRAFT-asterisk-odbc-menuselect-host-elf-signing` prepared as an upgrade to
PR #7632. It records only the generated `menuselect` ELF signing mechanism.
It does not claim that the 125 unregistered upstream inventory entries have
passed.

## Evidence chain

| ID | Evidence | Fixed version or environment | Result |
|---|---|---|---|
| EVID-01 | Official CI #36868 | Recipe before `a6ceb013f0` | `menuselect` was generated, then rejected at its first `--check-deps` execution after `chmod 755`; make reported error 126. |
| EVID-02 | `a6ceb013f0` | `archives/a/asterisk-odbc/22.10.1/conanfile.py` | Added `_sign_ohos_executable()` after the helper build and before `menuselect.makeopts`; it stages, removes a stale `.codesign`, self-signs, restores mode, and atomically replaces. |
| EVID-03 | Official CI #42701 | `a23d26ee75`, worker `OpenHarmonyPCDeveloper-CI-011` | Passed the package pipeline and consumer test. This is the authoritative CI result for the behavior-related recipe blob `be7f0df38e32917b540cbe6ed1e29080f7aa8fe5`. |
| EVID-04 | Current device execution | Asterisk 22.10.1 full test run tree | 599 tests registered. Excluding 5 protected framework self-tests, 594 ran in 80 root categories: 559 PASS, 26 FAIL, 9 NOT RUN. |
| EVID-05 | Current device package validation | Recipe rrev `a744e096...`, package revision `16c0f27d...` | Package build completed with the recursive-mutex patch; final `conan test` passed after probe support for the device `llvm-readobj`. |

## Test scope accounting

| Scope | Inventory | Current result | Notes |
|---|---:|---|---|
| Upstream Asterisk internal tests | 724 | 559 PASS / 26 FAIL / 14 SKIP / 125 not executed | `559/724` (77.21%). The 14 skips contain 9 runtime `NOT RUN` outcomes and 5 protected framework self-tests. |
| Current configured test-runner registrations | 599 | 594 normal entries executed | 80 clean root categories avoid duplicate nested-category execution; 125 source-inventory entries were not registered. |
| Package consumer probe | 1 | 1 passed at #42701 and current device | Current `conan test` validated 7 modules and 6 sample configs for the mutex recipe revision. |

## Boundary

The OHOS recursive-mutex initialization patch changes the recipe after
`a23d26ee75`. EVID-05 supplies its separate target-side package build and
consumer-test evidence; EVID-03 remains the historical official CI evidence
for the prior signing/linker recipe blob.

The test-runner exploration uses temporary device-only preload shims and a
locally rebuilt `test_strings.so`. They are not recipe inputs, are not shipped
with `asterisk-odbc`, and are excluded from this PR's product-validation claim.

## Reproduction entrypoints

```sh
git checkout a23d26ee75
CI_PACKAGES="archives/a/asterisk-odbc/22.10.1" zsh ci/conan/build_and_test.sh
```

The current test campaign has completed root-category isolation. To improve
source-inventory coverage, rebuild or configure the missing test modules and
run the 125 currently unregistered entries separately.
