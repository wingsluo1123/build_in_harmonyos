# f2fs-tools 1.16.0 task notes

## Source and build contract

- Task: DEP #15495; branch: `feat/f2fs-tools-1.16.0` on the task owner's fork.
- Upstream repository/tag: `https://git.kernel.org/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git`, `v1.16.0`.
- Peeled source commit/tree: `06c027abc6153c4a97cba5317844e8dcaaee3cf7` / `9c3ad82b3acaac8665211a7d7ad650879ef352af`.
- Mirror-covered static source archive: `https://github.com/kernelorg-mirror/linux_kernel_git_jaegeuk_f2fs-tools/archive/refs/tags/v1.16.0.tar.gz`, SHA-256 `cdb2c85e52e2fea075569fe661764dc026ad3640501add2aa9927f605596bc63`.
- Source URL decision for rule A/R39: keep this GitHub static archive as transport for the upstream `v1.16.0` tag. Kernel.org's Google Git mirror identifies the authoritative source as Jaegeuk's official git.kernel.org repository and confirms the pinned commit/tree. The GitHub `kernelorg-mirror` account labels its copies unofficial; this recipe does not treat GitHub as project ownership. Its archive endpoint is on the CI mirror-covered host list, R39 permits an archive of the matching mirror tag, and the SHA-256 pins the exact bytes. Checked canonical `cdn.kernel.org` release-path variants returned 404; the old SourceForge project says it is no longer maintained there. No git clone or generated `git.kernel.org` snapshot is used.
- The GitHub archive has `configure.ac` but no generated `configure`. CI build #97780 (buildbot id 112299) failed on old head `0b108c90` at `build()` line 61 because `bash autogen.sh` could not find `aclocal` (`Error 127`).
- The fix declares `autoconf/2.72`, `automake/1.18`, `libtool/2.5.4`, and `m4/1.4.19` as Conan `tool_requires`, supplies the declared build environment, and runs `autoreconf -fiv`. The four package recipes were found in the `ohpcd` registry.
- The recipe invokes make with `-j2`. It uses the native HarmonyOS `aarch64-unknown-linux-ohos` triplet and retains the five configure-probed library dependencies.
- One source portability patch replaces an unused `ldconfig` configure failure with a no-op fallback and copies the five `fsck.f2fs` aliases so package install does not depend on symlinks.

## Upstream test audit

`reports/upstream-test-inventory.tsv` declares all 113 source-defined cases: 108 `verify.sh` image resize/stress scenarios, one standalone 5,000-operation fsstress scenario, three SHA-512 `UNITTEST` vectors, and one SPO block-device/power-loss/reboot scenario. `reports/upstream-test-audit.md` records the counting commands and case boundary; `reports/upstream-test-results.tsv` records status, raw output, and cause for every case.

This CI-fix session records 0 pass, 0 fail, and 113 not-run. No device probe or HarmonyOS test was run: device use was explicitly unavailable for this session because the two seats were held by `fix-opm-common-15330` and `work-mpich-544`. Each case has a separate row in `reports/upstream-test-results.tsv`. The 109 resize/stress scenarios require a HarmonyOS F2FS loop-mount environment, root-equivalent mount permissions, `~/grub`, `~/xfstests/ltp/fsstress`, and isolated scratch storage. The three SHA-512 vectors were also not run; an earlier Windows MinGW compile attempt stopped at missing `mntent.h`, and there was no device session. The SPO case was not launched because it writes `/dev/sdb1`, changes sysrq controls, and forces a reboot; no disposable device seat was available.

## Consumer package checks

`test_package/run_consumer_checks.py` defines 12 actual-binary checks: seven tool/alias version dispatches, the `f2fs_io` and `f2fscrypt` help tables, the parser's missing-argument diagnostic, and mkfs/fsck against a disposable regular-file image. `reports/test-package-results.tsv` records all 12 as not-run for this session because no device seat or HarmonyOS target package was available. The runner emits one PASS/FAIL/SKIP record per case and a `TEST_PACKAGE-SUMMARY`; any failed assertion or unexpected process-start `OSError` returns nonzero. It returns zero only when there are no failed cases. If Conan's `can_run()` reports that no target runtime is configured, the runner emits all 12 as SKIP with the target/build context and a concrete runtime-unavailable reason. Temporary-workspace/image prerequisites keep their explicit per-case not-run reasons; none are counted as failures.

## Local validation and CI boundary

The exact local syntax, hook, and Conan export results are in `reports/local-validation.md`. No new-head CI or AI-review outcome is claimed here; no CI outcome is inferred from the old-head failure or local checks.


## 2026-10-18 CI #98101 follow-up

Buildbot #98101 (build id 112743) on `OpenHarmonyPCDeveloper-CI-038` failed in `conan-build-test` step 698081 because `--build` and `--host` were both `aarch64-unknown-linux-ohos`; Autoconf attempted to execute its compiled probe and reported `cannot run C compiled programs`. Only stdio log 588232 was exposed, not a separate `config.log`. The recipe now uses a distinct GNU/Linux build alias when build and host profiles are equal OHOS, preserves the OHOS host, scopes a build-local `TMPDIR` and umask 000 to configure, and relaxes generated configure temp-directory umasks following libthreadar commit `defdf7c277282d830dea4782eb5fcd5c1ddb26ac`.

Local AST/helper checks, Conan export `f2fs-tools/1.16.0#7892dbd2d61050ea84d1a2ce87fd73f8`, and Ubuntu 24.04 native source autoreconf/configure/`make -j2` passed. A separate system Autoconf 2.71 cross probe selected cross mode but its `config.sub` rejected the OHOS triplet; the recipe declares 2.72. These are local checks only, not OHOS test results. At 07:44 CST, the jump host was reachable but second hop `127.0.0.1:2200` returned `Connection refused`; no device session or target result exists. Upstream N=113 and consumer N=12 remain entirely not-run with per-case reasons.
