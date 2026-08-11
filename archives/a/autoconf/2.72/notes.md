# autoconf 2.72 adaptation notes

## Scope

- Target package: `autoconf/2.72`
- Branch: `docs/autoconf-2.72-retain-ohos-patches`
- Worktree: `D:\harmonyos\worktrees\autoconf`
- Issue: not found in local project files or handoff context; pending issue number in PR/handoff.
- Do not mix this into `libao`; `D:\harmonyos\worktrees\libao` was not modified.

## Version confirmation

- Repo/index: `archives/_index.yaml`, `SUMMARY.md`, and `scripts/ohc/dependency_resolver.py` point to Autoconf 2.72.
- Existing archive: `archives/a/autoconf/2.72` already existed but lacked `conanfile.py`, `conandata.yml`, `test_package`, and `commands.json`.
- Upstream: GNU FTP provides `autoconf-2.72.tar.gz`; downloaded SHA-256 is `afb181a76e1ee72832f6581c0eddf8df032b83e2e0239ef79ebedc4467d92d6e`.
- Source mirror note: PR CI build #15421 failed before recipe execution while downloading the PR diff from `gitcode.com`, not while downloading Autoconf. However, the same CI diagnostic says `ftp.gnu.org` is not reachable from the worker, so `conandata.yml` now tries TUNA, Aliyun, and `mirrors.kernel.org` GNU mirrors before falling back to the official GNU FTP URL. The SHA-256 remains the official tarball hash.
- Upstream also has newer Autoconf 2.73, but the current project dependency mapping still targets 2.72.

## W0 dependency and remote checks

Commands run:

```sh
conan list "autoconf/*" -r=ohpcd
conan download "autoconf/2.72" -r=ohpcd --only-recipe
conan list "m4/*" -r=ohpcd
conan download "m4/1.4.19" -r=ohpcd --only-recipe
conan list "m4/1.4.19:*" -r=ohpcd
conan download "m4/1.4.19" -r=ohpcd
conan list "perl/*" -r=ohpcd
conan list "perl/5.42.2:*" -r=ohpcd
conan download "perl/5.42.2" -r=ohpcd --only-recipe
conan list "automake/*" -r=ohpcd
conan list "libtool/*" -r=ohpcd
curl -I -L https://mirrors.tuna.tsinghua.edu.cn/gnu/autoconf/autoconf-2.72.tar.gz
curl -I -L https://mirrors.aliyun.com/gnu/autoconf/autoconf-2.72.tar.gz
curl -I -L https://mirrors.kernel.org/gnu/autoconf/autoconf-2.72.tar.gz
```

Results:

- `autoconf/*`: 0 matching recipes in `ohpcd`; direct download failed with `system acceleration policy not enabled`.
- `perl/5.42.2`: visible in `ohpcd`; recipe already present in local cache.
- `perl/5.42.2:*`: OHOS armv8 package `6b129b068851896169fae42d399fa922d239ce8a` visible in `ohpcd`.
- Earlier `m4/*` checks returned 0 recipes while the dependency adaptation was still pending.
- 2026-08-06 recheck after the `m4` merge: `m4/1.4.19` is visible in `ohpcd`; recipe revision `9a84a566238ea69b63e725d646354933` and OHOS armv8 package revision `8b566d24f4ee8ccaea3bc86a3eb00a93` downloaded successfully.
- `automake/1.18` and `libtool/2.5.4`: visible in `ohpcd`; useful for downstream `autoreconf`, but their adaptations belong to their own packages and are not rebuilt or vendored in this `autoconf` PR.
- 2026-08-07 source mirror check from local Windows: TUNA, Aliyun, and `mirrors.kernel.org` returned HTTP 200 for `autoconf-2.72.tar.gz`; USTC returned HTTP 403 and was not added; `ftpmirror.gnu.org` timed out in 30 seconds.

Dependency status:

- `m4/1.4.19` is no longer the active blocker for `autoconf/2.72`; the isolated OHOS device run now resolves and uses both `m4/1.4.19` and `perl/5.42.2` from `ohpcd`.

## Source and build-system analysis

- Official release tarball contains `configure`, `configure.ac`, `Makefile.in`, `bin/*.in`, and `build-aux/config.guess/config.sub`.
- The previous archive already had six OHOS patch files but no Conan recipe. Those patch files mixed real OHOS triplet support with generated outputs from a manual build (`bin/autoconf`, `lib/version.m4`, `tests/atconfig`, `tests/atlocal`) and embedded fixed device paths such as `/storage/Users/currentUser/...` and `/data/service/hnp/bin/...`.
- This Conan version keeps the old patch numbering and adaptation intent visible for review, but only applies the portable source patches that do not force maintainer-generated files to be rebuilt.
- Build system is Autotools; recipe uses `configure && make -j1 && make install`.
- No `autoreconf` is needed to build Autoconf itself.
- Autoconf installed commands are Perl scripts that need `perl`, `m4`, and the package's `share/autoconf` data directory at runtime.

## Changes prepared

- Added `conanfile.py` with `package_type = "application"`.
- Added `conandata.yml` with official GNU source URL, SHA-256, and patch declarations.
- Added software-level `commands.json` because Autoconf installs CLI commands.
- Added `test_package` that runs the installed commands, uses `autoconf`/`autoheader` to generate a minimal `configure` project, and directly exercises `autom4te` macro processing.
- Retained the previous OHOS patch file names for review traceability while keeping Conan's active patch set reproducible:
  - Applied by `conandata.yml`: `0001-support-linux-ohos-config-triplet.patch` and `0002-use-mkdir-for-config-status-tempdirs-on-ohos.patch`.
  - Retained/audited but not applied by `conandata.yml`: `0001-bin-autoconf.patch`, `0002-build-aux-config.guess.patch`, `0003-build-aux-config.sub.patch`, `0004-lib-version.m4.patch`, `0005-tests-atconfig.patch`, and `0006-tests-atlocal.patch`. The current active triplet patch already covers the portable `config.guess`/`config.sub` parts. The previous generated-file patches embedded fixed device paths. Applying source-template replacements for those generated-file names on the release tarball marks man page dependencies stale and makes `make` require missing maintainer tools such as `help2man`; Conan instead lets `configure` generate those files and the recipe wraps installed commands to provide relocatable Perl/macro paths.
- The active and audit `config.guess` patches use the shell-visible `uname -s` value `HarmonyOS` observed on the OHOS device on 2026-08-11; they do not add OHOS-specific preprocessor branches.
- Added wrapper scripts after install so `share/autoconf` paths are derived from the package prefix instead of baked absolute paths.
- The `autom4te` wrapper prepends the current package `share/autoconf` directory on every invocation. This compensates for upstream `autom4te.cfg` being configured with `//share/autoconf` when Conan installs with `DESTDIR`.

## Local verification

Checks run:

```powershell
python -m py_compile archives\a\autoconf\2.72\conanfile.py archives\a\autoconf\2.72\test_package\conanfile.py
conan export archives\a\autoconf\2.72
git -C <unpacked-autoconf-2.72> apply --check --verbose archives\a\autoconf\2.72\patches\0001-support-linux-ohos-config-triplet.patch
git -C <unpacked-autoconf-2.72> apply --check --verbose archives\a\autoconf\2.72\patches\0002-use-mkdir-for-config-status-tempdirs-on-ohos.patch
conan create archives\a\autoconf\2.72 --build=missing
conan create archives\a\autoconf\2.72 -pr:h=ci\conan\profiles\ohos-aarch64 -pr:b=ci\conan\profiles\ohos-aarch64 --build=autoconf/*
```

Results:

- Python syntax check: pass.
- YAML/JSON metadata parse check: pass.
- Patch apply check against the official 2.72 tarball: pass.
- `conan export`: pass; latest exported recipe revision after the review patch cleanup is `autoconf/2.72#ded5821bccb80a62dddc24f4b5002f07`.
- First `conan create`: blocked during dependency graph resolution because `m4/1.4.19` was not yet in local cache or `ohpcd`.
- 2026-08-06 `conan create` with OHOS profile: dependency graph resolved with `m4/1.4.19` and `perl/5.42.2` from cache/`ohpcd`.
- The same run initially caught stale hunk line numbers in the triplet-support patch; the patch set was refreshed and then applied successfully during Conan `source()`.
- Current local Windows limit: build reaches `autotools.configure()`, then fails with `'.' is not recognized as an internal or external command` because this host cannot execute the POSIX `configure` script under the OHOS profile. True OHOS runner verification has passed.
- 2026-08-07 true-device reruns with the current OHOS profile first exposed `CONFIG_SHELL=/data/service/hnp/bin/bash` from `ci/conan/profiles/ohos-aarch64`; that path is not present on the current device. The recipe now overrides `SHELL` and `CONFIG_SHELL` in the generated Conan build environment with the executable shell discovered by `_config_shell()`, which resolves to `/bin/sh` or `/system/bin/sh` on current OHOS devices. The profile also defines `PATH` directly, so test_package adds autoconf, m4, and perl package `bin` directories through an explicit `autoconf_test_env` script after `conanbuild`.
- 2026-08-08 review-fix rerun proved that applying template replacements for the retained generated-file patch names makes `make` try to regenerate man pages and fail because `help2man` is not installed on the device. The active Conan patch set therefore stays on the already verified triplet patch plus the OHOS temp-directory workaround; the generated-file patch names stay present for audit but are not listed in `conandata.yml`.
- 2026-08-09 PR CI revalidation build #16919 passed source download and dependency resolution, then failed during `autotools.configure()` with `./config.status: can't create ./conf*/subs1.awk: Permission denied`. This is the known OHOS/HMDFS Autoconf temp-directory case, not a mirror-source failure. Patch `0002-use-mkdir-for-config-status-tempdirs-on-ohos.patch` now keeps the OHOS controlled `mkdir` branch but relaxes its temp-directory `umask` from `077` to `022` in both the release `configure` script and `lib/m4sugar/m4sh.m4`, so generated `config.status` inherits the same behavior.

## OHOS isolated device verification

Initial Windows PowerShell SSH checks were blocked by the remote endpoint closing before the SSH banner. After the device window became available, the isolated job was created at:

```text
/storage/Users/currentUser/ohos-users/codex-autoconf/autoconf-2.72
```

Because the branch was not pushed, local `archives/a/autoconf` was transferred as a tarball and extracted only into the isolated repo:

```powershell
ssh -T -p 33332 -i "$env:USERPROFILE\.ssh\ohos_pc_codex_ed25519" currentUser@frp-tip.com
```

Runner command:

```sh
. "$HOME/ohos-users/codex-autoconf/autoconf-2.72/env.sh"
cp "$HOME/.conan2/settings.yml" "$CONAN_HOME/settings.yml"
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```

Final successful run after retaining/auditing the old OHOS patch names:

```text
/storage/Users/currentUser/ohos-test-runs/codex-autoconf-autoconf-autoconf-2.72-pr4410-review-patches-final-20260808-171755-20260808-171755-45265
```

Result:

- Exit code: 0.
- `L0_RESULT=pass: all checks passed`.
- `L1_RESULT=pass: test_package executed`.
- `L5_RESULT=pass: bin/ has content`.
- `L4_RESULT=warn: dangerous functions in patches`; warning comes from portability patch content and is non-blocking in this run.
- `L2_RESULT=skip`: generic direct `bin/* --version/--help` probe does not load Conan dependency PATH, so Perl-backed Autoconf wrapper commands cannot find `perl`/`m4` there. The explicit `test_package` runs with `env=["conanbuild", "autoconf_test_env"]` and verifies command startup by name, `autoconf`/`autoheader` generation, `autom4te` macro processing, generated `configure`, and `config.h.in`.

Additional test-package findings:

- Running generated `configure` is intentionally not part of the final smoke test because the runner user's `/tmp` behavior is inconsistent: shell here-doc temp files may attempt `/tmp/sh*.tmp` and fail with `Read-only file system`.
- `autoreconf --force --install` is not part of the final smoke test because it can call optional `aclocal`; Automake/libtool are handled as separate packages. This `autoconf` test verifies that the installed `autoreconf` command starts under the Conan runtime environment.

Successful package reference:

```text
autoconf/2.72#ded5821bccb80a62dddc24f4b5002f07:6b129b068851896169fae42d399fa922d239ce8a#8a1aae9d15192163ba32f34e79cdc95c
```

## Upstream `make check` on OHOS

After the Conan package L0/L1/L5 verification passed, a separate upstream Autotest run was executed from a clean source copy in the same isolated OHOS job area. This run was not added to the recipe build flow.

Run directory:

```text
/storage/Users/currentUser/ohos-test-runs/codex-autoconf-autoconf-autoconf-2.72-upstream-make-check-clean-sh-20260806-200600-13526
```

Source workdir:

```text
/storage/Users/currentUser/ohos-users/codex-autoconf/autoconf-2.72/upstream-check-clean-sh-20260806-200601/src
```

Command outline:

```sh
./configure --disable-dependency-tracking --disable-silent-rules
make -j1 MAKEINFO=true
make check -j1 MAKEINFO=true TESTSUITEFLAGS="-j1"
```

The test environment used `perl/5.42.2` and `m4/1.4.19` from the isolated Conan cache, set `PERL5LIB` for packaged Perl modules, used `/bin/sh` as `SHELL`/`CONFIG_SHELL`, and kept `TMPDIR`/`TMPPREFIX` inside the isolated job directory. Generated Autotools files were timestamp-adjusted after copying the Conan source cache so the run would not try to rebuild release-generated files with missing `aclocal-1.16`.

Result:

- Exit code: 2.
- Official summary: `ERROR: 539 tests were run, 247 failed (5 expected failures). 70 tests were skipped.`
- Inventory: 609 GNU Autotest cases total; 70 skipped; 539 non-skipped cases executed.
- Pass-rate statement for PR: 297/539 (about 55.1%) when counting 292 `ok` cases plus 5 expected failures as expected outcomes; 242 unexpected failures remain.
- The 242 unexpected failures were classified from `tests/testsuite.log` and representative `testsuite.dir/*/testsuite.log` files:
  - 236 failures are generated-configure probe tests that complete the macro probe but then fail Autoconf's `ath_fn_check_env` clean-environment assertion. The OHOS `/bin/sh`/ksh compatibility layer changes dynamic shell variables such as `BASHPID`, `EPOCHREALTIME`, and `KSH_MATCH` between the before/after snapshots; representative groups include `acc.at`, `semantics.at`, `acheaders.at`, `actypes.at`, and `acfunctions.at`.
  - The largest source-file clusters are `semantics.at` 38, `actypes.at` 35, `acfunctions.at` 30, `acspecific.at` 23, `acgeneral.at` 22, `acheaders.at` 22, `acc.at` 20, and `acprograms.at` 17.
  - Several early tool/shell cases fail on concrete OHOS filesystem behavior: `tools.at:145` reports shell here-doc temporary files under `/tmp/sh*.tmp` as `Read-only file system`; `base.at:977` shows directory canonicalization/diagnostic bytes changing for `--prefix=/usr//`; `tools.at:672` fails timestamp ordering (`configure -nt configure.1`).
  - Compiler-probe logs repeatedly show OHOS clang/ld diagnostics that Autoconf's generic test harness records in `config.log`, for example `ld.lld: error: undefined symbol: main` during compiler-version probing and clang rejecting legacy `-V`/`-qversion`/`-version` options. The compiler itself is usable for package build and `test_package`; these failures are upstream macro self-test assumptions interacting with the OHOS shell/toolchain environment.

## Next OHOS device / shadow CI commands

After the branch is pushed, rerun from a fresh isolated repo with:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex-autoconf \
  --job autoconf-2.72 \
  --package archives/a/autoconf/2.72 \
  --repo-source "$HOME/validation/build_in_harmonyos"

. "$HOME/ohos-users/codex-autoconf/autoconf-2.72/env.sh"
cd "$CI_REPO_ROOT"
git fetch origin docs/autoconf-2.72-retain-ohos-patches
git checkout docs/autoconf-2.72-retain-ohos-patches
sh "$OHOS_JOB_BASE/run-conan-heavy.sh"
```

Single-package CI command once inside the isolated repo:

```sh
CI_PACKAGES="archives/a/autoconf/2.72" zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/a/autoconf/2.72
```
