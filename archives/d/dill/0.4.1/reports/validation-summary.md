# dill 0.4.1 test report

Date: 2026-10-13 (Asia/Shanghai). Device: HarmonyOS HongMeng Kernel 1.12.0, AArch64; CPython 3.12.9; Conan 2.29.1. Dedicated cache and device-specific profile; shared CI scripts unchanged.

## Results and counting unit

| Suite | Total | Passed | Failed | Skipped | Unit |
| --- | ---: | ---: | ---: | ---: | --- |
| Upstream official runner | 30 | 30 | 0 | 0 | Distinct script processes, not assertion or test-function count |
| Installed consumer | 14 | 14 | 0 | 0 | unittest cases |

The 30 scripts include 28 object/API scripts and 2 child-interpreter integration scripts (`test_check.py`, `test_session.py`). Five conditional functions in those scripts do not exercise their optional branches: test_dtype, test_array_nested, test_array_subclass, test_numpy, test_lambdify, because NumPy/SymPy are not installed. They are not five additional failed/skipped script processes. All 30 official runner scripts actually execute; 30/30 script success does not mean 100% optional-branch coverage. Complete entry list and commands are in test_package/MANIFEST.yml.

Consumer cases cover origin/version, pickle protocols, lambdas, closures, dynamic classes, recursive aliases, streams, file-content mode, module sessions, fresh-interpreter deserialization/origin, temp APIs, source introspection, undill payload and helper help. Removal of installed lib gives exit 1; restoration gives 14/14. Relocation gives 14/14 and bare undill without PYTHONPATH succeeds. These reruns do not add cases to the denominator.

## Build and CI

Official URL conan create builds the Python distribution via setuptools/84.0.0. Its first consumer run exposed two test harness errors (bare-name posix_spawn lookup and using dumpIO without loadIO/seek), fixed in consumer code; no upstream assertion changed. Final W3 invokes original setup.sh/build_and_test.sh and succeeds: L0/L1/L2/L4/L5 pass. L4 has no native payload/patch to inspect. The W3 negative gate also confirms actual package dependency.

Dedicated-cache parallel download first failed in ThreadPool/SemLock with ENOSPC; parallel=1 still uses a pool, parallel=0 selects the serial path and retrieves the published binary. First W3 attempt lacked Bash/Git; final validation adds only process-local paths to existing published tool binaries. These are environment findings, not library source fixes.

## Modifications and limitations

No upstream source/test/runner modified. The recipe adds portable helper launchers around unchanged upstream script resources, with --help support and relative package/resource lookup. Optional graph/profile image generation and NumPy/SymPy object coverage remain unverified. Upstream deprecated license classifiers and deliberately disabled build byte-compilation produce warnings; packaging contains sources only. Current-HEAD remote CI, human review, official knowledge admission, merge and publication require separate remote evidence.

## Original-log integrity

W3 log SHA256: `3a116567bc09eb57566c1c17a8d5c8951dd5b238ad700587f9d1323f691ca6b6`. Receipt integrity and raw byte hash verified. Raw logs and runtime receipts are not committed; path-b-evidence.md retains hashes and boundaries.

Final original ConanVerifier overall verdict: PASS. G1/G2/G3 actually run; G0 skips unknown build-system prequery, G4 cannot find a package ID, and its L2/L4/L5 skip without a cache path. These legacy-tool omissions are disclosed; original W3 executes its actual five gates and the independent 61-file/negative/relocation proof covers the real no-user/channel package. It required the standard export/apply patch interfaces even for a patch-free package; they are now present and make no source changes.
