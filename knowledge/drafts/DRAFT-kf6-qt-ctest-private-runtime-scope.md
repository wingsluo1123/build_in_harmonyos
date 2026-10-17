# Keep the private Qt runtime inside the KF6 CTest invocation

## Trigger and controlled result

On a HarmonyOS PC AArch64 device, the KSyntaxHighlighting 6.18.0 Conan recipe
built six upstream Qt Test executables with `-c tools.build:jobs=2`. The recipe's
runtime context ran CTest successfully: **6/6 CTest entries**, **1038/1038 Qt
Test PASS records**, zero failures and zero skips. A separate bare SSH shell
reran `ctest --test-dir BUILD -V` against the same binaries with no private Qt
runtime path. It failed **6/6** in roughly 0.17 seconds. A sample error was:

```text
Error relocating .../bin/folding_test: qt_version_tag: symbol not found
Error relocating .../bin/folding_test: _ZN7QObjectD2Ev: symbol not found
```

Adding only `BUILD/bin` and the Conan Qt package's `lib` directory to that
invocation's `LD_LIBRARY_PATH` made the same six binaries pass in about 15.5
seconds. Its Qt Test totals were 22, 114, 38, 288, 288 and 288. The consumer
package also linked and ran a binary that loaded the bundled C++ syntax and
Breeze Light theme.

## Mechanism and repair

The link step and test step have separate library lookup contexts. Conan's
`Environment.vars(self).apply()` affects the recipe's `ctest` call only; it
does not set the environment for a later manual SSH command. A successful link
therefore does not prove that a bare shell resolves the same private Qt runtime.
The relocation errors occur before any Qt Test case starts and differ from a
normal failed assertion.

In a Conan recipe, obtain the Qt and KF6 package folders from `self.dependencies`.
Prepend their `lib` and plugin paths, plus the build's library directory, to
an `Environment` that surrounds the actual CTest call. On this device, the
recipe also materializes shared-library aliases beside test executables to
support the OHOS loader. Scope these changes to test execution rather than
exporting a global `LD_LIBRARY_PATH` before `conan create`.

Do not set `BUILD_TESTING=OFF`, exclude failing CTest entries, or count the
relocation failures as upstream behavior without repeating the test in the
recipe's dependency runtime. Keep the outer CTest count and inner Qt Test
count distinct: 6 executable registrations versus 1038 PASS records here.

## Boundary against existing knowledge

The checked `origin/main` tip was
`b544378a4ea82b4959135eebb21f5e509eeebf91` (2026-10-15), with 547 formal
`knowledge/graph/*.kv` entries. A file-level search of
`knowledge/graph/*.kv` and `knowledge/doc/*.md` found one Qt6/KF6 + CTest
record, E344. It concerns excluding multimedia integration tests when an OHOS
media backend is unavailable. A second file-level search for
`qt_version_tag` and `symbol not found` together returned zero graph/doc files.
This draft records the narrower, unrepresented mechanism: a controlled
bare-shell-versus-Conan-environment rerun in which omitting the private Qt6
runtime changes the same six KF6 CTest executables from pass to Qt-symbol
relocation failures.

Nearby entries and drafts have different failure signatures or remedies:

| Entry | Its failure | Difference here |
|---|---|---|
| E019 | A shared library cannot be found | Here the library is found, but the selected Qt runtime lacks the linked symbols. |
| E344 | Excluding multimedia integration tests when OHOS has no media backend | This run executed all eight registered tests; no test was removed or excluded. |
| E505 | Global `LD_LIBRARY_PATH` overrides RPATH and breaks symlink aliases | This draft scopes the private Qt path to the CTest invocation and does not alter toolchain subprocesses. |
| E520 | The Qt6 `qsb` build tool cannot load Qt6 ShaderTools at build time | This draft concerns already-linked KF6 tests at test time. |
| E537 | Absolute `DT_NEEDED` leakage from a KF6 package without SONAME | No claim is made that `DT_NEEDED` was rewritten or leaked here. |
| E736 draft | Missing HarmonyOS CMake platform module disables build-tree RPATH and tests cannot find shared libraries | This run reached the test binaries; the distinguishing failure is Qt-symbol relocation when the private Conan Qt runtime is absent. |
| E666 draft | Qt5 ABI mismatch and a missing `QSqlDriver::notification(QString)` symbol | It covers Qt5 supply-line mismatch and plugin construction; this case uses Qt6 and a missing runtime search path. |

The test does not identify which fallback Qt provider the bare shell selected;
the established finding is that removing the private runtime path changes
six successes into six relocation failures. A second independent upstream
project has not yet been used to validate this pattern, so the draft remains
open for editor review before promotion.

## Reproduction and provenance

Run `ctest --test-dir BUILD -V` against the existing build tree first with
`LD_LIBRARY_PATH` unset, then with `BUILD/bin:QT_PACKAGE/lib`; keep all binaries,
test files and other environment variables the same. The task-local recipe,
consumer and test report are under
`archives/k/ksyntax-highlighting/6.18.0/`. Source event: task #15161,
2026-10-15. Contributor: `iKalous_OscarP`.
