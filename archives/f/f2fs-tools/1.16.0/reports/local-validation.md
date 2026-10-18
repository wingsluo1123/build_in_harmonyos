# Prior local validation attempt (pre-CI-fix, 2026-10-18)

Date: 2026-10-18. These checks validate the recipe and source patch; they do not establish a HarmonyOS device build.

| Check | Result | Evidence |
| --- | --- | --- |
| Recipe and test-package Python syntax | PASS | `python -m py_compile` completed for `conanfile.py`, `test_package/conanfile.py`, and `test_package/run_consumer_checks.py`; a later AST parse also passed. |
| YAML parse | PASS | `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml` loaded with `yaml.safe_load`. |
| Conan export | PASS | `conan export stage-f2fs-tools-15495/candidate/archives/f/f2fs-tools/1.16.0` exported `f2fs-tools/1.16.0#032d491ba6e0dd03f6d67b0a78fbe6a7`. |
| OHPCD build-tool recipe lookup | PASS | `conan list "autoconf/2.72" -r=ohpcd`, `automake/1.18`, `libtool/2.5.4`, and `m4/1.4.19` each found one recipe. This lookup does not claim a HarmonyOS binary package was installed. |
| Conan pre-commit hook | PASS with one warning | The hook checked one recipe and exited 0. Its sole warning is L0g recommending a GitCode URL; the selected GitHub URL is the required mirror-covered static source archive. No blocking hook errors remained. |
| Portability patch apply check | PASS | `git apply --check -p1` against the extracted v1.16.0 source returned exit 0. |
| Static source archive checksum | PASS | SHA-256 for `f2fs-tools-1.16.0-kernelorg-mirror.tar.gz` is `cdb2c85e52e2fea075569fe661764dc026ad3640501add2aa9927f605596bc63`, matching `conandata.yml`. |

## Device and upstream execution boundary

At 2026-10-18 07:44 CST, the prescribed two-hop check reached the jump host but SSH to second hop `127.0.0.1:2200` returned `Connection refused`. The device session could not be opened. As a result, no `conan create`, package consumer run, or device-side upstream test was performed; the per-case not-run records are in `upstream-test-results.tsv` and `test-package-results.tsv`.

A local attempt to compile the upstream SHA-512 test on the Windows MinGW host stopped before execution with `stage-f2fs-tools-15495/upstream/tools/sha512.c:23:10: fatal error: mntent.h: No such file or directory`. This host-header limitation is recorded as not-run for the three vectors; it is not reported as a test failure or a HarmonyOS result.

The buildbot failure on old head `0b108c90` remains the reported real CI evidence: `aclocal: command not found`, followed by Conan Error 127 in `build()`. No new-head CI result is inferred from these local checks.

## CI-fix session local validation (2026-10-18)

These checks validate the consumer result gate and recipe metadata only. No `conan create`, upstream case, device run, or CI run was started.

| Check | Result | Evidence |
| --- | --- | --- |
| Python AST and YAML parse | PASS | Parsed the recipe, both test-package Python files, and `conandata.yml`, `manifest.yaml`, `test_package/MANIFEST.yml`. |
| Runtime-unavailable path | PASS | Local simulation printed 12 per-case SKIP records, `total=12 pass=0 fail=0 notrun=12`, exit 0. No package binaries were invoked. |
| Unexpected process-start error path | PASS | Synthetic `PermissionError` simulation was counted as 11 FAIL cases plus the dependent fsck case not-run; runner exit was 1. No package binaries were invoked. |
| Conan export | PASS | `conan export archives/f/f2fs-tools/1.16.0` exported `f2fs-tools/1.16.0#032d491ba6e0dd03f6d67b0a78fbe6a7`. |
| Source archive pin | PASS | Local archive SHA-256 `cdb2c85e52e2fea075569fe661764dc026ad3640501add2aa9927f605596bc63` matches `conandata.yml`; archive has one root directory. |
| Patch whitespace | PASS | `git diff --check -- archives/f/f2fs-tools/1.16.0` returned 0. |

Upstream N=113: 0 pass, 0 fail, 113 not-run. All 12 consumer checks are separately not-run. No device test ran because the 2026-10-18 07:44 CST two-hop check reached the jump host but SSH to `127.0.0.1:2200` returned `Connection refused`. CI #97890 and #97932 were already classified as platform-wide Conan SemLock `ENOSPC` before recipe execution; this session did not poll CI or AI review.


## Latest configure failure and local revalidation (2026-10-18)

Buildbot #98101 / build id 112743 on worker `OpenHarmonyPCDeveloper-CI-038` failed at `conan-build-test` step 698081. The only exposed raw log was stdio log 588232; Buildbot provided no separate `config.log` artifact. Its configure command passed identical OHOS `--build` and `--host` triplets, so configure attempted to run a compiled probe and failed with `cannot run C compiled programs`. The recipe now uses distinct build and host triplets for that equal-profile case, keeps the real OHOS host, scopes build-local `TMPDIR` and umask 000 to configure, and relaxes generated configure temp-directory umasks.

The current recipe AST/triplet/umask assertions and Conan export passed (`f2fs-tools/1.16.0#7892dbd2d61050ea84d1a2ce87fd73f8`). Ubuntu 24.04 native source `autoreconf`, configure, and `make -j2` passed on the pinned archive plus package patch; the build used native x86_64 GNU build/host triplets and is not an OHOS result. A local cross probe with system Autoconf 2.71 entered cross mode, but that version's `config.sub` rejected `aarch64-unknown-linux-ohos`; the recipe requires Autoconf 2.72.

At 07:44 CST the jump host was reachable and the second hop `127.0.0.1:2200` returned `Connection refused`. No `conan create`, HarmonyOS package consumer test, upstream case, or device build ran. Full upstream N=113 is 0 pass, 0 fail, 113 not-run; all 12 consumer checks are not-run. The detailed ledgers retain a technical reason for every case.
