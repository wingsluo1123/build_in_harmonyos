# Upstream test inventory and execution audit

## Source and registration audit

- Upstream tag: `v1.16.0`, peeled commit `06c027abc6153c4a97cba5317844e8dcaaee3cf7`, tree `9c3ad82b3acaac8665211a7d7ad650879ef352af`.
- Mirror-covered static source archive: `https://github.com/kernelorg-mirror/linux_kernel_git_jaegeuk_f2fs-tools/archive/refs/tags/v1.16.0.tar.gz`, SHA-256 `cdb2c85e52e2fea075569fe661764dc026ad3640501add2aa9927f605596bc63`.
- Rule A/R39 source decision: retain the GitHub static archive of the `v1.16.0` tag copied from upstream. Kernel.org's Google Git mirror confirms the authoritative repository and pinned commit/tree. The GitHub `kernelorg-mirror` account labels its copies unofficial, so it is used only as mirror-covered transport for the matching upstream tag; `github.com` is in the CI mirror host list, R39 permits this static mirror-tag archive, and SHA-256 pins the bytes. Checked canonical `cdn.kernel.org` release-path variants returned 404; the old SourceForge project states it is no longer maintained there. No git.kernel.org snapshot or git clone is used.
- `Makefile.am` lists `man lib mkfs fsck tools`; it declares no Automake `TESTS` or `check_PROGRAMS` target.
- `.github/workflows/ci.yml` is a seven-entry build matrix (Android, Linux GCC/Clang, x86 GCC, powerpc64 GCC, MinGW64 GCC, and macOS); its job runs autogen/configure/make and contains no test step.
- The tracked source tree has no `tests/` directory. Assertion-bearing tests are in `scripts/verify.sh`, `scripts/spo_test.sh`, and the `UNITTEST` section of `tools/sha512.c`.
- `scripts/dumpf2fs.sh` and `scripts/tracepoint.sh` are diagnostics without pass/fail assertions.

## Counted cases and command

The inventory contains 113 individually named cases. The nine matrix sizes are `4, 5, 8, 11, 16, 25, 32, 55, 64` GiB; `C(9,2)=36` source/destination pairs in each of three modes. Each scenario also executes nested operations: 360 resize calls, 612 fsck calls, 252 mount/unmount calls, and 180 `fsstress -n 10000` calls, plus the standalone `fsstress -n 5000` case. Nested operations are disclosed but are not counted as independent registered scenario invocations.

The count can be reproduced from the source list with:

```sh
python3 - <<'PY'
from itertools import combinations
sizes = (4, 5, 8, 11, 16, 25, 32, 55, 64)
print("matrix", 3 * len(list(combinations(sizes, 2))) )
print("total", 3 * len(list(combinations(sizes, 2))) + 1 + 3 + 1)
PY
```

The independent-case definitions are 36 `from_sload ~/grub` pairs, 36 `from_sload $TARGET` pairs, 36 `from_mount $MNT` pairs, one standalone stress invocation, three SHA-512 vectors (empty message, `abc`, and the standard long message), and one SPO `start` scenario. `reports/upstream-test-inventory.tsv` is the compact inventory; `reports/upstream-test-results.tsv` adds per-case result, raw evidence, and technical cause.

## This CI-fix session's results

| Family | Declared | Pass | Fail | Not-run |
| --- | ---: | ---: | ---: | ---: |
| `scripts/verify.sh` resize/stress scenarios | 109 | 0 | 0 | 109 |
| `tools/sha512.c` `UNITTEST` vectors | 3 | 0 | 0 | 3 |
| `scripts/spo_test.sh start` | 1 | 0 | 0 | 1 |
| **Total upstream** | **113** | **0** | **0** | **113** |

No HarmonyOS device test was run in this session. At 2026-10-18 07:44 CST, the two-hop check reached the jump host but the second hop `127.0.0.1:2200` returned `Connection refused`; no device session opened. All 109 `verify.sh` scenarios are individually marked not-run because they require a HarmonyOS F2FS loop-mount environment, root-equivalent mount/umount permission, the `~/grub` fixture or target source, `~/xfstests/ltp/fsstress`, and isolated scratch storage; no case command was started.

The three SHA-512 vectors were not executed. The 2026-10-18 07:44 CST second-hop refusal prevented target execution; an earlier local Windows MinGW compile attempt stopped at `stage-f2fs-tools-15495/upstream/tools/sha512.c:23:10: fatal error: mntent.h: No such file or directory`, so no local executable was available either.

The SPO case was not launched. Its upstream start path hard-codes `/dev/sdb1`, inserts a kernel module, changes sysrq controls, and forces a reboot. No HarmonyOS device session opened after the second-hop `127.0.0.1:2200` connection refusal, and no explicitly disposable target was assigned. This is a not-run result, not a test pass.

The 12 package consumer checks are separate from upstream N and are listed in `reports/test-package-results.tsv`. This session did not run `conan create`, build/install the HarmonyOS package, or execute consumer checks; the second-hop connection refusal prevented a device session. all 12 are individually recorded not-run because the 2026-10-18 07:44 CST second hop returned `Connection refused` and no HarmonyOS session was opened. CI #97890 and #97932 failed before recipe execution in Conan's SemLock with `OSError: [Errno 28] No space left on device`, matching the platform-wide infrastructure failure; they are not recipe or consumer-test results. The new head's CI result was not observed.

## Build failure and recipe correction

The real old-head CI failure was build #97780 / buildbot id 112299 at `0b108c90`. Raw log lines:

```text
f2fs-tools/1.16.0: RUN: bash autogen.sh
autogen.sh: line 3: aclocal: command not found
ConanException: Error 127 while executing
```

The GitHub release archive includes `configure.ac` but no generated `configure`. The recipe now declares `autoconf/2.72`, `automake/1.18`, `libtool/2.5.4`, and `m4/1.4.19` as Conan build tools, constructs a controlled bootstrap environment (native HNP Perl when present, pure-Perl Autotools module paths, and cleared inherited Perl overrides), and runs `autoreconf -fiv`. The four tool recipes were found in `ohpcd`. The recipe continues with `Autotools.configure()` and `make -j2`; it no longer asks the worker to run the unqualified upstream `autogen.sh`.

No row above is caused by a missing dependency library. The five runtime/build libraries remain declared in the recipe. The new head's CI result was not polled, so the bootstrap correction and this consumer-gate fix are supported by source inspection and local recipe validation only; no successful CI build is claimed.

## Consumer result-gating changes

The consumer runner now returns a nonzero exit code when any case is `FAIL`; explicit `SKIP`/not-run cases do not increment the failure count. `test_package/conanfile.py` calls `self.run` without `ignore_errors=True`, allowing Conan to fail the test package on that nonzero result. An unexpected process-start `OSError` is a failed case. If `can_run()` is false, the runner prints all 12 case identities as not-run with target/build context and a concrete runtime-unavailable reason. Temporary-workspace/image prerequisites retain their explicit not-run reasons. Missing package executables remain failures when the target runtime is runnable; recipe dependencies remain declared and imported.
