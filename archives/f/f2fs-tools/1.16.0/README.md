# f2fs-tools 1.16.0

Conan package candidate for the official upstream `v1.16.0` tag. It builds the native command-line utilities and static helper libraries for the `aarch64-unknown-linux-ohos` HarmonyOS PC target. The source archive and commit are pinned in `conandata.yml` and `manifest.yaml`.

The source archive contains `configure.ac` but no generated `configure`. The recipe declares `autoconf/2.72`, `automake/1.18`, `libtool/2.5.4`, and `m4/1.4.19` as Conan build tools, then runs `autoreconf -fiv`; it does not rely on a worker's ambient `aclocal`. The remaining recipe keeps the blkid, SELinux, LZO2, and LZ4 dependencies, static build, `LDCONFIG` fallback, and copied `fsck.f2fs` aliases.

The pinned source URL is a GitHub static archive of the `v1.16.0` tag copied from the upstream kernel.org tree. The authoritative kernel.org Google Git mirror confirms the source repository and tag commit `06c027abc6153c4a97cba5317844e8dcaaee3cf7` / tree `9c3ad82b3acaac8665211a7d7ad650879ef352af`. The GitHub `kernelorg-mirror` account describes its copies as unofficial, so it is used only as a mirror-covered transport for the matching upstream tag; the pinned SHA-256 `cdb2c85e52e2fea075569fe661764dc026ad3640501add2aa9927f605596bc63` fixes the bytes. This follows rule A/R39 and avoids generated git.kernel.org snapshots and git clone.

## Validation results

The local recipe syntax, YAML parse, Conan export, and Conan pre-commit hook are recorded in `reports/local-validation.md`. The OHPCD registry lookup found all four declared build-tool recipes.

The upstream inventory is 113 cases. This session recorded 0 pass, 0 fail, and 113 not-run in `reports/upstream-test-results.tsv`. No HarmonyOS test ran: at 2026-10-18 07:44 CST the two-hop check reached the jump host but SSH to second hop `127.0.0.1:2200` returned `Connection refused`. The 109 resize/stress cases need device F2FS loop-mount/root access, `~/grub`, `~/xfstests/ltp/fsstress`, and isolated scratch storage. The three SHA-512 vectors were not run; an earlier Windows MinGW compile attempt stopped because `mntent.h` was unavailable. The `spo_test.sh start` case writes `/dev/sdb1`, changes sysrq controls, and forces a reboot, so it was not launched without a disposable device seat.

The 12 package consumer checks are recorded separately in `reports/test-package-results.tsv`; the HarmonyOS package was not built or installed in this no-device session. Consumer assertion failures and unexpected process-start errors now fail `conan test`; the runner exits zero only when the failure count is zero. A Conan `can_run()` false result is recorded as 12 explicit not-run cases with the target/build context. The buildbot failures #97890 and #97932 were platform-wide Conan SemLock `OSError: [Errno 28] No space left on device` before the recipe ran; they are infrastructure failures, not package results. No new-head CI result is claimed, and CI was not polled in this session.


## CI #98101 follow-up

Buildbot #98101 (build id 112743), worker `OpenHarmonyPCDeveloper-CI-038`, failed in `conan-build-test` step 698081 during configure. Its only exposed log was stdio log 588232; it passed identical `--build=aarch64-unknown-linux-ohos` and `--host=aarch64-unknown-linux-ohos`, then failed with `cannot run C compiled programs`. The recipe now makes the OHOS host explicit and uses a distinct GNU/Linux build alias when both Conan profiles are OHOS. Configure also uses a scoped build-local TMPDIR and umask 000, and generated configure temp-directory umasks are relaxed.

Local recipe validation passed AST/helper assertions and Conan export `f2fs-tools/1.16.0#7892dbd2d61050ea84d1a2ce87fd73f8`. A native Ubuntu 24.04 source autoreconf/configure/`make -j2` passed; it is not an OHOS result. The local Autoconf 2.71 cross probe selected cross mode but its `config.sub` rejected the OHOS triplet; the recipe requires Autoconf 2.72. No new-head CI outcome is claimed.
