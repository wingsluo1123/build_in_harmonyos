# vcprompt 1.3.0 HarmonyOS adaptation notes

## Pull request

- MR: `https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/14356`
- Branch: `feat/vcprompt-1.3.0` (commit `b4a569e4f4`)
- Contrib task: `11629` (A 类)
- PR body follows `templates/积分赛事PR模板.md` (test-case comparison, upstream
  test changes, complemented tests, verification results)

## Scope

- Worktree: `D:\harmonyos\worktrees\vcprompt`
- Branch: `feat/vcprompt-1.3.0`
- Archive path: `archives/v/vcprompt/1.3.0`
- Contrib task: `11629` (A 类)
- Upstream: powerman fork of `gward/vcprompt` (Homebrew `vcprompt`, GPL-2.0-or-later)

## W0 dependency check

vcprompt links no third-party library. git / hg / svn / cvs / fossil are *runtime*
peers, not build dependencies: the VCS state is read from on-disk metadata
(`.git/HEAD`, `.hg/dirstat`, `.svn/entries`, `CVS/Tag`, ...), and external
binaries are only spawned for the optional `%u` (unknown files) and `%m`
(modified files) format specifiers.

The only optional dependency in `configure.ac` is sqlite3 (`--with-sqlite3`),
needed for svn >= 1.7 working copies. This recipe builds with
`--with-sqlite3=no` and therefore declares **no** Conan requirement, so there is
no dependency PR to split out. sqlite3 is published in the registry
(`conan download sqlite3/3.53.4 -r=ohpcd --only-recipe` succeeded from this
host) if a later revision wants to enable svn 1.7/1.8 support.

Build-time tool that is *not* shipped in the tarball and is *not* present on the
OHOS device image: `autoconf` (and its `m4` backend). The GitHub tag archive
contains `configure.ac`, `config.h.in`, `Makefile.in` but no `configure`, and a
device probe found `autoconf`, `autoheader`, `m4` all MISSING in
`/data/service/hnp/bin`, `~/usr/local/bin` and `~/.local/bin`. The recipe
therefore declares `tool_requires("autoconf/2.72")` and
`tool_requires("m4/1.4.19")`; ohpcd publishes prebuilt binaries for both with
`os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15`:

```text
conan download "autoconf/2.72" -r=ohpcd --only-recipe   => recipe present
conan download "m4/1.4.19"    -r=ohpcd --only-recipe   => recipe present
(on the device) conan list "autoconf/2.72:*" -r=ohpcd
  => revisions ded5821bccb80a62dddc24f4b5002f07, package 6b129b068851896169fae42d399fa922d239ce8a
(on the device) conan install --requires=m4/1.4.19 --requires=autoconf/2.72 --update
  => downloaded m4/1.4.19 + autoconf/2.72 + perl/5.42.2 (build requirement of
     autoconf); `m4 --version` => GNU M4 1.4.19, autoconf runs after PERL5LIB is
     pointed at the perl package
```

`automake` is *not* needed: `configure.ac` has no `AM_INIT_AUTOMAKE`, and
`autoreconf -i` would only be required to regenerate the auxiliary build files,
which the recipe supplies itself (see decision 3). The `automake` query from the
Windows host failed with the host-side accelerator-policy error rather than a
"not found", so it is *inconclusive* — it does not matter here.

## Source and build system analysis

- Version tag tarball: `https://codeload.github.com/powerman/vcprompt/tar.gz/refs/tags/v1.3.0`
  (tag `v1.3.0` → commit `f73334253ec764a463125206762ce6bac0c39e4b`)
- sha256: `3db5ebad2e333d43b464b665c8d43b35156b0f144052f10c340a5c5007a6874d`
- License: GPL-2.0-or-later (declared in every source header; the tarball ships
  no license file, so `licenses/LICENSE` is the verbatim GPL-2.0 text already
  vendored in this repository at `archives/t/tinyproxy/1.11.3/docs/COPYING`)
- Build system: GNU autotools, but *generated*: `configure.ac` + `Makefile.in` +
  `config.h.in` → `autoconf` → `./configure` → `make`.
- Sources: `src/*.c` — `vcprompt.c`, `common.c`, `capture.c`, `git.c`, `hg.c`,
  `svn.c`, `cvs.c`, `fossil.c` (8 files, no `bzr.c`; the `bzr.h` include in
  `vcprompt.c` is commented out upstream).
- Product: single executable `vcprompt` (355-line `main`), plus a manual page
  `vcprompt.1` and a Perl helper `vcprompt-hgst`.

### Configurability notes

- `config.h` is only consumed by `src/vcprompt.c` and `src/svn.c`; the only
  interesting flag is `HAVE_SQLITE3`, which `config.h.in` derives from
  `HAVE_SQLITE3_H && HAVE_LIBSQLITE3`. With `--with-sqlite3=no` the svn backend
  keeps the 1.3-1.6 `entries` parsers and drops only the sqlite 1.7/1.8 path —
  no empty stub is introduced, the code path is the one upstream itself
  supports when sqlite is absent.
- `HAVE_SQLITE3` is the only `#if`-guarded feature; everything else in
  `config.h.in` is cosmetic (PACKAGE_* strings, autoconf type fallbacks).
- The Makefile has no `@`-substitution lines, so `config.status` only has to
  write `Makefile` and `config.h` — relevant for the HMDFS note below.

## Adaptation decisions

1. **`autoconf` before `configure`.** The tarball has no `configure`, so
   `build()` runs `self.run("autoconf", cwd=self.source_folder)` and fails hard
   if the script was not produced. Same pattern as `archives/b/bird/3.1.6`.
2. **sqlite3 disabled** (`--with-sqlite3=no`). Keeps the package
   self-contained; `test_package` asserts that `vcprompt -F` does *not*
   advertise `svn-1.7`/`svn-1.8`, so the built configuration is observable.
3. **`config.guess`/`config.sub` are shipped by the recipe.** The generated
   `configure` refuses to run without them:

   ```text
   configure: error: cannot find required auxiliary files: config.guess config.sub
   ```

   The tarball does not ship them (upstream produces its release tarball with
   `hg archive`, which never contained them) and `autoreconf -i` would pull in
   automake plus its Perl module tree. `autotools/config.guess` and
   `autotools/config.sub` are therefore copied next to `configure.ac` before
   `autoconf` runs. The GNU `config.guess` shipped inside the autoconf package
   prints `aarch64-unknown-linux-ohos` on the device; the shipped 48-line
   `config.guess` reproduces exactly that string from `uname -m`, matching the
   approach already used by `archives/b/bird2/2.17.4`.
4. **HMDFS `config.status` temp directories (E011/E052/E129/E136).** Autoconf
   creates its temporary directory under `umask 077`; HMDFS then produces
   `drwx--S---` and blocks file creation inside it. Reproduced verbatim on the
   device with autoconf 2.72:

   ```text
   ./config.status[697]: can't create ./conf49901-963/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```

   On OHOS the generated `configure` is patched `umask 077` → `umask 022`
   (E129's documented fix) before `./configure` runs; after the patch the same
   build produced `config.status: creating Makefile` / `creating config.h` and
   completed. A missing `umask 077` pattern is a **hard error** rather than a
   warning, so a silently unpatched build cannot be published.
   `TMPDIR` is additionally pointed at a probed writable directory
   (`/data/service/hnp/tmp`, `/storage/Users/currentUser/tmp`, `/var/tmp`,
   `/tmp`) and exported to the build environment.
5. **Serial `make` on OHOS.** `make -jN` tries to create a jobserver FIFO, and
   `mkfifo` is denied on the hmdfs data partition:

   ```text
   make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo47485: Operation not permitted
   ```

   make continues (the build itself still succeeds), but the recipe builds
   serially on OHOS to keep the log clean; the project is 8 small C files.
6. **No writable `/tmp` for the upstream assert suite.** `tests/common.sh`
   hardcodes `mktemp -d /tmp/vcprompt.XXXXXX`. Patch `0001` changes that single
   line to `${TMPDIR:-/tmp}` so the suite works both on OHOS and on hosts with a
   normal `/tmp`. The patch touches no assertion and no test logic. Verified on
   the device: the suite passes with `TMPDIR=/storage/Users/currentUser/tmp` and
   also leaves `tmpdir` intact for the cleanup trap.
7. **Two of the five upstream suites are executed: `check-simple` and
   `check-git`.** `make check` = `check-simple check-hg check-git check-svn
   check-fossil`. `check-simple` needs no external tool (it builds fake
   CVS/git/fossil/hg/svn metadata by hand); `check-git` needs a real git binary
   plus its generated `git-repo.tar` fixture, and the OHOS image provides git
   (verified on the device: `/data/service/hnp/bin/git` 2.45.2), so it runs too.
   `check-hg`, `check-svn` and `check-fossil` need Mercurial, Subversion and
   Fossil, which are neither in the image nor published on ohpcd; those three
   suites are not executed and are recorded in `test_package/MANIFEST.yml`.
   Executed assertions: 46 (check-simple) + 8 (check-git) = **54, 0 failures**.
8. **Only `vcprompt` is installed.** `make install` also installs
   `vcprompt-hgst`, a 122-line Perl script; packaging it would add a Perl
   runtime dependency for an auxiliary feature, so the wanted artifacts (binary
   plus man page) are copied explicitly.
9. **ELF signing.** On OHOS, `bin/vcprompt` is stripped of an old `.codesign`
   section and re-signed with `binary-sign-tool -selfSign 1` (ML-0043), then
   `chmod 755` (the signing step can drop the execute bit). Signing is skipped
   with a warning when the tool is absent (e.g. a cross/SDK-only environment).
10. **L2 smoke-test caveat.** `make check-simple` asserts that `vcprompt -h`
    exits **non-zero** (upstream behaviour); the CI L2 probe runs
    `vcprompt --version` and then `vcprompt --help`, both of which vcprompt treats
    as an unknown option and exits 1 on. L2 is therefore expected to report
    `warn`/non-pass for this package; the real CLI evidence comes from
    `make check-simple` (L1) and the `test_package` assertions.

11. **In-source build.** `configure` writes the generated `Makefile` into the
    source tree and that Makefile's own `Makefile:` rule needs `Makefile.in`
    next to it, so an out-of-source build fails with

    ```text
    make: *** No rule to make target 'Makefile.in', needed by 'Makefile'.  Stop.
    ```

    `layout()` therefore sets `self.folders.build = "src"`, which is how
    upstream builds this project. Editing the generated `Makefile` instead would
    violate R6 (only source templates may be patched).

## Upstream tests

```text
make check         # check-simple check-hg check-git check-svn check-fossil
make check-simple  # executed by this recipe (no external tool needed)
make check-git     # executed by this recipe (needs a real git binary)
```

`tests/test-simple` covers, among others: no working copy, `/`, CVS
(`Entries`/`Tag`, subdirectories), git (broken `.git`, detached HEAD, branch,
subdirectory), fossil (`_FOSSIL_`/`.fslckout`), hg (branch file, bookmarks, MQ
patches, revlog inlined/non-inlined), svn (`entries` file and XML formats,
truncated entries), a non-readable parent directory, `VCPROMPT_FORMAT`
precedence, a trailing `%`, and the `-h` exit status/help text.

`tests/test-git` covers the specifiers that need a real repository:
`%b` (branch), `%m` (modified) and `%u` (unknown/untracked) inside a git
working copy that `tests/setup-git` generates.

Result on the device (2026-10-02, `TMPDIR=/storage/Users/currentUser/tmp`):

```text
./test-simple: all tests passed
./test-git: all tests passed
```

54 assertions (46 + 8), 0 failures. `check-hg`, `check-svn` and `check-fossil`
were not executed: Mercurial, Subversion and Fossil are not installed on the
device and are not published on ohpcd.

## Consumer test

`test_package` needs no compiler: it runs the packaged executable and asserts

1. `vcprompt -f %n:%b` inside a hand-written git working copy prints exactly
   `vcprompt:ohos-vcprompt-test`;
2. the default format `"[%n:%b] "` still carries the branch;
3. `vcprompt -F` lists `git hg cvs fossil svn-1.6` and does **not** list
   `svn-1.7`/`svn-1.8` (proves the `--with-sqlite3=no` build);
4. a directory tree with no VCS metadata prints nothing.

This is a real dependency on the package: with `bin/` removed the binary is
missing and the test fails, which is what the CI destructive L1e check verifies.

**CI-only pitfall fixed in this PR (build #67833 → fixed).** The fixtures were
originally created under `self.build_folder`. On the platform CI worker the
repository is checked out at
`/storage/Users/currentUser/.cache/buildbot-worker/conan-pr-check/build`, i.e.
**inside a git repository**, so for the "no working copy" assertion vcprompt
walked up from the fixture and found that repository's `.git`, reporting
`git:main` instead of empty output:

```text
ERROR: vcprompt/1.3.0 (test package): Error in test() method, line 86
	ConanException: expected no output outside any working copy, got 'git:main'
```

The same run passed locally because Conan's own build folder
(`~/.conan2/p/b/.../b`) is not inside any repository. The fixtures and the
captured output now live in `tempfile.mkdtemp()` (i.e. `TMPDIR`, which the
worker sets to `/data/storage/el2/base/cache` — outside the checkout), so the
assertion is independent of where the recipe is unpacked. `test_package/test.sh`
was updated the same way (`mktemp -d` instead of a path inside the caller's cwd)
and its `%n` expectation corrected from `vcprompt:<branch>` to `git:<branch>`.

**AI review follow-up (P2/P3, fixed in this PR).** The first review round raised
three non-blocking issues in the new files; the two that were real are fixed:

1. **P2 — `test_package/test.sh` fixture layout.** The script created the fake
   `.git` at `$workdir/.git`, i.e. on an *ancestor* of `$workdir/no-vc/nested`
   used by the fourth assertion, so that assertion always saw
   `git:ohos-vcprompt-test` and the script failed even with a correct package.
   Fixed by giving the git fixture its own subdirectory
   (`$workdir/fixture/.git`), exactly like `FIXTURE_DIR` in `conanfile.py`;
   assertions 1/2/3 now run from `$fixture` while assertion 4 keeps using
   `$workdir/no-vc/nested`.
   A second, related defect surfaced while verifying the fix: `vcprompt -F`
   prints one feature per line, and the membership test padded the whole capture
   with spaces (`case " $features " in *" svn-1.6 "*)`), which cannot match a
   newline-separated list. The capture is now folded with `tr '\n' ' '`.
   Verified on the device: 10 passes / 0 failures under both the default shell
   and `/bin/sh`.
2. **P3 — `config.guess` triplet mismatch.** The header claimed the OHOS triplet
   reproduced the GNU original, but the `OHOS_SYSROOT` branch was dead code (the
   device does not export that variable) and the script printed
   `aarch64-unknown-ohos` while the GNU original prints
   `aarch64-unknown-linux-ohos`. The dead branch is gone and HarmonyOS now maps
   to the `linux-ohos` kernel field, so both print the same string; `config.sub`
   normalises both spellings idempotently. Verified on the device:
   `config.guess` → `aarch64-unknown-linux-ohos`, and `configure` reports
   `checking build system type... aarch64-unknown-linux-ohos` /
   `checking host system type... aarch64-unknown-linux-ohos`.
3. **P3 — `pipefail` in `test.sh`** (optional, not applied): the script is
   `#!/bin/sh` and POSIX `sh` has no `pipefail`; `set -eu` is used instead.

Additionally, the review's per-file table mentioned — without raising it as a
finding — that `config.sub`'s `linux-gnu*` → `linux` rule **dropped the libc
suffix**. That was a real divergence from the GNU original, so it was fixed as
well: `config.sub` now fills the vendor field for two-component triplets and
keeps any libc suffix. Measured against the GNU original on the device (from the
`autoconf` package, timestamp 2023-09-19), 7 of 10 representative inputs are now
byte-identical:

```text
x86_64-pc-linux-gnu        -> x86_64-pc-linux-gnu          (GNU: same)
x86_64-linux-gnu           -> x86_64-pc-linux-gnu          (GNU: same)
aarch64-unknown-linux-gnu  -> aarch64-unknown-linux-gnu    (GNU: same)
aarch64-unknown-linux-ohos -> aarch64-unknown-linux-ohos   (GNU: same)
aarch64-unknown-ohos       -> aarch64-unknown-ohos         (GNU: same)
arm64-apple-darwin20       -> aarch64-apple-darwin20       (GNU: same)
i686-pc-linux-gnu          -> i686-pc-linux-gnu            (GNU: same)
```

The three remaining differences are documented limits, none reachable from this
recipe (annotated in the file header): `aarch64-linux-ohos` keeps the explicit
`linux` vendor, there is no os-alias expansion such as
`gnueabihf` → `linux-gnueabihf`, and `sun4` is passed through — that last one
only has to exit 0, because it is the probe `configure` runs to validate
`config.sub`, which it does.

End-to-end after the change, on the device: `autoconf` regenerates `configure`,
`./configure --with-sqlite3=no` reports
`checking build system type... aarch64-unknown-linux-ohos` /
`checking host system type... aarch64-unknown-linux-ohos` and creates
`Makefile` + `config.h`, `make` succeeds, and both `check-simple` and
`check-git` report `all tests passed`.

## Shadow CI on the device (2026-10-12) — full pipeline, PASSED

While the platform's buildbot worker was down (see below), the device-local
shadow runner was used to run the whole pipeline end to end. It is the project's
own runner:

```sh
# device, from a worktree whose HEAD contains archives/v/vcprompt/1.3.0
sh "$HOME/validation/run-ohos-shadow-ci-local.sh" archives/v/vcprompt/1.3.0
```

It materialises a clean tree with `git archive HEAD`, builds an **isolated**
`HOME`/`CONAN_HOME`/`TMPDIR` under `$HOME/ohpc-ci-shadow/runs/<sha>-<stamp>-<pid>/`,
generates its own `ci/conan/profiles/ohos-local` (clang 15 wrapper with
`--sysroot`+`-fuse-ld=lld`, `CONFIG_SHELL`/`SHELL` pointing at the real bash),
then runs `ci/conan/setup.sh` and `ci/conan/build_and_test.sh`.

Result (58 s, rc=0):

```text
[ok] L0: All quality gate checks passed
vcprompt/1.3.0: RUN: make check-simple -j1   -> ./test-simple: all tests passed
vcprompt/1.3.0: RUN: make check-git -j1      -> ./test-git: all tests passed
vcprompt/1.3.0: Package '6b129b068851896169fae42d399fa922d239ce8a' built
vcprompt/1.3.0: signed OHOS binary: vcprompt
[ok] L1a: test_package was executed by conan create
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on vcprompt
[ok] L5: bin/ has content
[warn] L2: vcprompt --version/--help failed (non-blocking)

L0_RESULT=pass  L1_RESULT=pass  L2_RESULT=skip  L4_RESULT=pass  L5_RESULT=pass
Total: 1   Success: 1   Failed: 0
```

The consumer assertions all passed, including `[ok] no working copy -> empty
output`, and `ci-metadata.json` records the same five gate results plus
`source_trace` (URL + sha256) and `build_trace` (profile `ohos-local`,
runner `local-ohos-shadow`, commit `4fb903a7eec1`).

Run directory: `~/ohpc-ci-shadow/runs/4fb903a7eec1-20261012T072502Z-32771`
(`logs/build_and_test.log`, `repo/archives/v/vcprompt/1.3.0/ci-metadata.json`).

## Platform CI status (why this MR shows CI failures)

The platform's buildbot worker was broken for an extended window on 2026-10-02 →
2026-10-12: builds are dispatched but die in `worker-prep` with

```text
eSSH bridge exec failed: connect failed: connection lost before ready:
Connection was refused by other side: 111: Connection refused
p rogram finished with exit code -1
```

so `git-clone`, `conan-build-test` and `cleanup` never run. This is **not
specific to this recipe** — a survey of the currently open MRs at the time showed
the same signature on several unrelated packages (`yamcha`, `rrsync`,
`lepton-eda`, ...) while a few others did reach the build step.

Chronology for this MR:

| build | worker | outcome |
|---|---|---|
| #67833 | CI-034 | reached `conan-build-test`; failed on the `no-VCS` assertion → fixed in `b24edd5fda` |
| #67871 / #67872 / #67883 / #68787 | 023 / 002 / 023 / 023 | failed before the build; worker network restriction |
| #75791 / #77093 | 014 | reached the pipeline flow; **source download timeout** → mirrored URL, see below |
| #87328 … #87931 (10 builds) | 041 | `git-clone` step: `FileNotFoundError: [Errno 2] No such file or directory: b'/system/xbin/git'` |

The last group is the current blocker and is **not** fixable from this recipe:

* worker `CI-041` uses a different build root
  (`/data/storage/el2/base/files/ci-worker/worker/conan-pr-check/build`) than
  CI-002/014/023/034 (`~/.cache/buildbot-worker/conan-pr-check/build`), and its
  image has no `git` where the runner looks for it, so `git-clone` fails,
  `conan-build-test` never starts, and `cleanup` then fails with
  `zsh: can't open input file: ci/conan/cleanup.sh` (exit 127);
* the other reachable workers (002/014/023) cannot reach the source hosts;
* every build from 2026-10-12T23:52 onwards was placed on worker 041, so
  re-triggering only produces more of the same failure.

This is reported in the MR instead of being worked around: the recipe already
builds and passes both on a correctly configured CI worker (#67833 reached
`conan-build-test`) and through the device shadow runner.

### First fully-scheduled platform run (2026-10-13)

Build `#88854` on worker `CI-030` is the first attempt that ran every step:

| step | result |
|---|---|
| worker_preparation / worker-prep | pass |
| git-clone | pass |
| checkout-pr | pass |
| conan-setup | pass |
| conan-build-test | fail — `configure: fork: retry: Resource temporarily unavailable` |
| cleanup | pass |

The recipe-side gates all passed (`L0` including L0i/L0j/L0k/L0m/L0n, `KC`, `JC`,
mirror rewrite of the source URL), and the build proceeded into `configure`. The
failure is the worker running out of process slots:

```text
/storage/Users/currentUser/.cache/conan2/p/b/vcpro332443d90e0f1/b/src/configure: fork: retry: Resource temporarily unavailable
checking for gcc... /data/service/hnp/bin/clang
checking whether the C compiler works... no
configure: error: C compiler cannot create executables
ConanException: Error 77 while executing autotools.configure()
```

Note this worker also reports `tools.build:compiler_executables` pointing at
`/data/service/hnp/bin/clang` — the same device-specific path discussed in the
“Environment gaps” section above; the recipe cannot influence that, and the
compiler test never actually ran because `fork()` failed first.

An earlier attempt in the same batch (`#88844`, worker `CI-016`) also reached the
pipeline and failed only in the pre-download step because that worker image has
no `curl` at all (`[Errno 2] No such file or directory: 'curl'`), after which
conan's own download could not reach the source host.

The `fork` exhaustion on `CI-030` reproduced on build `#89215` (93
`fork: retry: Resource temporarily unavailable` lines). `configure` forks once
per compiler probe, so a worker whose process slots are exhausted cannot get past
`checking whether the C compiler works...`; nothing in the recipe can avoid those
forks, and the same recipe compiles and passes on the device and in the shadow
runner. Retries are therefore spaced out rather than repeated back-to-back.

Build `#89505` (worker `CI-016`) hit the same limit even earlier — `autoconf`
itself could not start:

```text
vcprompt/1.3.0: RUN: autoconf
/storage/Users/currentUser/.cache/conan2/p/autoc39bb48086335e/p/bin/autoconf[2]: can't fork - try again
ConanException: Error 1 while executing
```

Measured on the same device while idle: `kernel/pid_max = 65536`,
`vm/max_map_count = 65535`, 178 processes, load average ≈ 20, and 40 consecutive
`fork`s all succeeded. The limit therefore binds only while several builds run
concurrently on the shared machine, which is why the identical recipe passes in
the shadow runner and fails intermittently on the platform.

### Platform CI PASSED — build #90180 (worker CI-006, 2026-10-13T22:43)

```text
## CI 校验通过
| 目标 | 构建 | Worker |
| PR #14356 | #90180 | OpenHarmonyPCDeveloper-CI-006 |

### 验证详情
- Conan test_package: 通过
- L0 门禁 (结构完整性): 通过
- L1 门禁 (测试执行验证): 通过

### 构建步骤
worker_preparation ✅  worker-prep ✅  git-clone ✅  checkout-pr ✅
conan-setup ✅  conan-build-test ✅  cleanup ✅
```

This is the official platform verdict on the recipe as committed: every step of
the pipeline ran and the conan gate suite passed. It was obtained after the
resource-exhaustion window above; retries were spaced ~25 minutes apart so as not
to contend with other builds on the shared machine.

### Source download on the platform worker

`#75791` failed with `类别: 网络问题 / 问题: 源码下载超时 / 原因: Worker 网络受限`
while `source()` was the only thing running. Measured from the device:

```text
codeload.github.com/powerman/vcprompt/tar.gz/refs/tags/v1.3.0          200  32004B  3.48s
github.com/powerman/vcprompt/archive/refs/tags/v1.3.0.tar.gz          200  32004B  1.73s
gh-proxy.com/https://github.com/powerman/vcprompt/archive/refs/...    200  32004B  0.87s
```

All three serve the **same bytes** (sha256 `3db5eba…a6874d`, same top-level
directory `vcprompt-1.3.0/`, same 37-entry file list), verified on the device.

`ci/conan/build_and_test.sh` rewrites source URLs into a mirror list, but its
pattern only matches URLs that start with `github.com/` — `codeload.github.com`
is not rewritten. The recipe therefore uses the `github.com/.../archive/...`
form as the primary URL, which the CI rewrites to a list led by `gh-proxy.com`
(confirmed in a shadow CI run: `Sources correctly downloaded from
https://gh-proxy.com/https://github.com/powerman/...`). The direct
`codeload.github.com` URL is kept in the recipe as a second attempt for the case
where every mirror in that list fails.

### `ci-metadata.json` `source_trace.url` is empty (platform script issue)

After the mirror rewrite the field cannot be extracted, and this is **not
specific to this recipe**:

* the rewrite turns the scalar into a list, so the first line matching the key is
  a bare `url:`;
* the extraction command is
  `grep -E '^\s*url:' … | head -1 | sed 's/^\s*url:\s*//'`, and the device's
  `grep` is **toybox 0.8.12**, where `\s` is not a whitespace class. Measured on
  the device against a control package (`archives/7/7zip/23.01/conandata.yml`,
  a plain scalar URL from www.7-zip.org): the same command returns an empty
  string, and so does the POSIX-class variant.

`sha256` is still recorded correctly in `ci-metadata.json`, and that is the
authoritative provenance value (the recipe verifies it on download), so the
missing URL is cosmetic. There is deliberately no extra `url`-ish key in
`conandata.yml` that could displace the mirror list as the first match.

Re-triggering was throttled after that to avoid queue spam, and the shadow CI run
above was used instead to obtain full-pipeline evidence.

## Local verification

Everything below was executed on the Windows host before touching the device.
`reports/` is git-ignored for this path, so the evidence is recorded here.

```text
# 1. source tarball
Invoke-WebRequest https://codeload.github.com/powerman/vcprompt/tar.gz/refs/tags/v1.3.0
Get-FileHash -Algorithm SHA256 -> 3db5ebad2e333d43b464b665c8d43b35156b0f144052f10c340a5c5007a6874d
=> matches conandata.yml (32004 bytes)

# 2. recipe syntax
python -B -m py_compile archives/v/vcprompt/1.3.0/conanfile.py \
                         archives/v/vcprompt/1.3.0/test_package/conanfile.py
=> exit 0

# 3. metadata parses
python -c "yaml.safe_load(...)" for conandata.yml, test_package/MANIFEST.yml,
  archives/v/vcprompt/manifest.yaml, archives/v/vcprompt/1.3.0/manifest.yaml
python -c "json.load(...)" for archives/v/vcprompt/commands.json
=> all OK

# 4. conan export + conan source in an isolated CONAN_HOME
CONAN_HOME=D:\harmonyos\tmp\conan-vcprompt-check
conan export <recipe> --user=ohpcd --channel=stable
=> Exported: vcprompt/1.3.0@ohpcd/stable#514ffe002e7413714479acc96fc7606f
   Copied: conandata.yml, conanfile.py, 0001-tests-common.sh-honour-TMPDIR.patch
conan source <recipe> --user=ohpcd --channel=stable
=> Sources correctly downloaded from https://codeload.github.com/powerman/vcprompt/tar.gz/refs/tags/v1.3.0
   Uncompressing vcprompt-1.3.0.tar.gz to .
   (src/ contains configure.ac, config.h.in, Makefile.in, src/*.c, tests/*)

# 5. patch validity
git apply --check -p1 <patch>              => exit 0 on the pristine tarball
patch_ng.fromfile(<patch>).apply(root=<pristine tree>, strip=1)  # Conan's own patcher
=> True, tests/common.sh line 64 becomes
   tmpdir=`mktemp -d "${TMPDIR:-/tmp}/vcprompt.XXXXXX"`
(the patch is a plain unified diff without a `diff --git`/`index` header so that
 ci/conan/hooks/pre-commit L0f, which requires the first line to start with
 `---`, also accepts it)

# 6. repository pre-commit L0 checks (ci/conan/hooks/pre-commit)
imported as a module and run against archives/v/vcprompt/1.3.0
=> 0 errors; 2 warnings: L0d (test() calls self.run() through the _run helper,
   the hook only scans the direct body) and L0g (github.com source URL — the CI
   adds the gh-proxy.com mirror fallback automatically for github.com URLs)
```

Not possible locally: the real `conan create` / `make check-simple` run on a
Windows host. This machine has no `make` (checked: `Get-Command make` is empty),
and the MinGW gcc present here cannot compile the upstream sources at all — it
stops at `sys/wait.h`, `arpa/inet.h`, `struct itimerval`, `SIGALRM` and `fork()`,
which are POSIX-only.

## Device verification (HarmonyOS PC, 2026-10-02)

Device: `ssh -p 56267 -i ~/.ssh/ohos_pc_codex_ed25519 currentUser@frp-tip.com`,
`HarmonyOS HongMeng Kernel 1.12.0 aarch64`, `$HOME=/storage/Users/currentUser`.

Device toolchain:

```text
python3 3.12.9 · conan 2.31.1 · make 4.4.1 · git 2.45.2 · cmake, zsh, clang 15 present
autoconf / autoheader / m4 / perl : MISSING in PATH, /data/service/hnp/bin, ~/usr/local/bin
mkfifo: Operation not permitted (hmdfs)  → make -jN jobserver warning
```

Steps executed, with results:

```text
1. tarball sha256 on the device (sha256sum)
   => 3db5ebad2e333d43b464b665c8d43b35156b0f144052f10c340a5c5007a6874d  (matches)

2. conan install --requires=m4/1.4.19 --requires=autoconf/2.72 --update
   (isolated CONAN_HOME=$HOME/validation/vcprompt-conan-home, device ohos-aarch64 profile)
   => downloaded m4/1.4.19 6b129b068851896169fae42d399fa922d239ce8a (ohpcd)
      downloaded autoconf/2.72 ded5821bccb80a62dddc24f4b5002f07 (ohpcd)
      downloaded perl/5.42.2 (build requirement of autoconf)
   => `m4 --version` => GNU M4 1.4.19
   => autoconf needs PERL5LIB=<perl pkg>/lib/perl5, otherwise
      "Can't locate strict.pm in @INC"

3. autoconf on the pristine tarball
   => configure generated (5705 lines); only warning is
      "configure.ac:18: warning: The macro 'AC_PROG_CC_C99' is obsolete."

4. ./configure (no config.guess/config.sub) => FAIL
   => "configure: error: cannot find required auxiliary files: config.guess config.sub"
   After copying the GNU config.guess/config.sub shipped by the autoconf package:
   => config.guess prints aarch64-unknown-linux-ohos

5. ./configure (with config.guess/config.sub) => FAIL, E129 reproduced
   => "./config.status[697]: can't create ./conf49901-963/subs1.awk: Permission denied"
      "config.status: error: could not setup config files machinery"

6. sed -i 's/umask 077/umask 022/g' configure  (the recipe does exactly this) => PASS
   => config.status: creating Makefile / creating config.h

7. make => PASS
   => clang -g -O2 -c src/{capture,common,cvs,fossil,git,hg,svn,vcprompt}.c
      clang -o vcprompt ...   (only -Wunused-command-line-argument warnings from
      the OHOS clang wrapper)

8. smoke
   => ./vcprompt -F  => cvs hg git fossil svn-1.3 svn-1.4 svn-1.5 svn-1.6
   => in a fake .git/HEAD working copy: ./vcprompt -f '%n:%b' => git:ohos-vcprompt-test
   => outside any working copy: empty output, exit 0

9. make check-simple (after patch 0001, TMPDIR=$HOME/tmp)
   => ./test-simple: all tests passed   (46 assertions, rc=0)

10. make -j2 => jobserver mkfifo warning only; build still OK
    plain make => OK        make -j 1 => OK
```

Conclusion: the recipe's build sequence (autotools helpers + autoconf + E129
umask patch + serial make + `make check-simple` + TMPDIR patch) is verified on
the device up to and including the upstream assert suite.

## Single-package CI on the device (2026-10-02, PASSED)

Command (from the repository root; `archives/v/vcprompt/1.3.0` is the only
package in scope):

```sh
CI_PACKAGES="archives/v/vcprompt/1.3.0" zsh ci/conan/build_and_test.sh
```

Result:

```text
[ok] L0: All quality gate checks passed
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on vcprompt
[ok] L5: bin/ has content
[warn] L2: vcprompt --version/--help failed (non-blocking)

L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: vcprompt version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
[step] All packages built and tested successfully
```

Evidence inside the run (`~/logs/vcprompt-ci-20261002-212720.log` on the device,
310 lines, the final run against this committed recipe; identical earlier runs
are in `~/logs/vcprompt-ci-20261002-212344.log` and `...-211857.log`):

```text
vcprompt/1.3.0: patched configure: umask 077 -> umask 022 (HMDFS/E129)
config.status: creating Makefile / creating config.h
vcprompt/1.3.0: RUN: make check-simple -j1
./test-simple: all tests passed                     # 46 upstream assertions
vcprompt/1.3.0: signed OHOS binary: vcprompt        # binary-sign-tool
vcprompt/1.3.0: Package '6b129b068851896169fae42d399fa922d239ce8a' built
vcprompt/1.3.0 (test package): [ok] %n:%b -> git:ohos-vcprompt-test
vcprompt/1.3.0 (test package): [ok] default format -> [git:ohos-vcprompt-test]
vcprompt/1.3.0 (test package): [ok] -F -> cvs hg git fossil svn-1.3 svn-1.4 svn-1.5 svn-1.6
vcprompt/1.3.0 (test package): [ok] no working copy -> empty output
ci-metadata.json: L0 pass / L1 pass / L2 skip / L4 pass / L5 pass
```

L2 is `skip`/`warn` for the documented reason (upstream vcprompt has no
`--version`/`--help`; it exits 1 on them), and L1e confirms the consumer test is
not a stub: with `bin/` moved away the test fails.

### Environment gaps found while running CI (infrastructure, not this recipe)

Two paths in `ci/conan/profiles/ohos-aarch64` do not exist on this device image
and had to be overridden for the run (the repository files were **not** changed;
the corrected copy was a device-local profile named `ohos-aarch64-devicefix`):

| Profile entry | Value in repo profile | Reality on the device |
|---|---|---|
| `CONFIG_SHELL` / `SHELL` | `/data/service/hnp/bin/bash` | missing; bash is at `~/usr/local/bin/bash`, profiles shipped on the device use `/bin/sh` |
| `tools.build:compiler_executables` | `/data/service/hnp/bin/clang[++]` | missing; clang 15 is at `~/usr/local/bin/clang[++]` |
| `LD_LIBRARY_PATH` | `.../ohos-sdk_26.0.0.18/ohos/native/llvm/lib` | path absent on this device |

Symptoms without the override:

```text
configure[139]: /data/service/hnp/bin/bash: inaccessible or not found
ConanException: Error 127 while executing           # autotools.configure()

configure:3110: /data/service/hnp/bin/clang -O3 -DNDEBUG conftest.c >&5
./configure: /data/service/hnp/bin/clang: inaccessible or not found
configure: error: C compiler cannot create executables
```

Suggested infrastructure fix (separate PR, out of scope here): make these
entries resolve per-device, e.g. `/bin/sh` for `CONFIG_SHELL`/`SHELL` and
`~/usr/local/bin/clang` (or no `tools.build:compiler_executables` at all so
Conan falls back to `PATH`).

## Reproducing the device run

The verification above was produced without committing anything on the device, so
the device's in-progress `librecast-test` checkout stayed untouched:

```sh
# device: dedicated worktree for this library
cd "$HOME/validation/build_in_harmonyos"
git worktree add "$HOME/validation/worktrees/vcprompt" -b feat/vcprompt-1.3.0 origin/main

# copy archives/v/vcprompt/ into that worktree (tar stream over ssh), then:
cd "$HOME/validation/worktrees/vcprompt"
export TMPDIR="$HOME/tmp" TMPPREFIX="$HOME/tmp/zsh"
CI_PACKAGES="archives/v/vcprompt/1.3.0" zsh ci/conan/build_and_test.sh
```

Until the CI profile is fixed (see the environment-gaps table above) the run
needs a profile whose `CONFIG_SHELL`/`SHELL` and `compiler_executables` point at
paths that exist, e.g.:

```sh
cp ci/conan/profiles/ohos-aarch64 "$HOME/.conan2/profiles/ohos-aarch64-devicefix"
sed -i 's|/data/service/hnp/bin/bash|/bin/sh|g' \
       "$HOME/.conan2/profiles/ohos-aarch64-devicefix"
sed -i 's|/data/service/hnp/bin/clang|/storage/Users/currentUser/usr/local/bin/clang|g' \
       "$HOME/.conan2/profiles/ohos-aarch64-devicefix"
CONAN_PROFILE=ohos-aarch64-devicefix \
  CI_PACKAGES="archives/v/vcprompt/1.3.0" zsh ci/conan/build_and_test.sh
```

Shadow CI runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/v/vcprompt/1.3.0
```

Manual interactive run on the device:

```sh
cd archives/v/vcprompt/1.3.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Device pre-flight for a fresh worker (per the真机避坑指南):

```sh
command -v autoconf m4 make sh git
mkdir -p "$HOME/tmp-probe" && TMPDIR="$HOME/tmp-probe" sh -c 't=$(mktemp); echo ok > "$t"; cat "$t"'
```

Observed result of the single-package CI on 2026-10-02: `Total: 1, Success: 1`,
`L0=pass`, `L1=pass` (`make check-simple` + `test_package`), `L4=pass`,
`L5=pass`, `L2` non-pass per decision 10 above.
