# mcookie 2.42.2 adaptation notes

## Scope

- Package: `mcookie/2.42.2`
- Upstream source: `util-linux-2.42.2.tar.xz`
- Task name: `mcookieC++`
- Branch: `feat/mcookie-2.42.2`
- Build system: Autotools

## Upstream identity

`mcookie` is not an independent C++ project. It is a C command in the util-linux
suite (`misc-utils/mcookie.c`). The task name's `C++` suffix is a language
annotation, not the upstream repository name. The actual source is the official
util-linux 2.42.2 release (SHA256
`03a05d3adf9602ef128f2da05b84b3205ce60c351e5737c0370f74000679ce8a`, verified by
real download on 2026-10-16).

## Build

Only `mcookie` is enabled:

```text
--disable-all-programs
--enable-mcookie
```

**Important (new knowledge, DRAFT-util-linux-default-on-tools-enable-option):
mcookie is a "default-on" util-linux tool — `UL_BUILD_INIT([mcookie], [yes])`
with no `AC_ARG_ENABLE` registration. The stock `configure` therefore does NOT
recognize `--enable-mcookie`; with `--disable-all-programs` the tool is silently
disabled, `make` only recurses `po/`, and the package has no binary while
`conan create` still exits 0. The focused build works only because
`patches/0002-ohos-register-enable-mcookie.patch` registers the option in the
`ac_user_opts` whitelist and makes the mcookie build-state block honor
`$enable_mcookie` (same pattern applies to the other 11 default-on tools:
isosize/mkswap/look/namei/getopt/renice/setpgid/setsid/colcrt/colrm/rev).**

All other util-linux libraries and programs are disabled. `mcookie` needs no
external Conan dependency: `misc-utils/Makemodule.am` links it against
`libcommon.la` plus the internal `lib/md5.c`; entropy comes from
`lib/randutils.c` (`getrandom()` when `HAVE_GETRANDOM` is detected, else
`/dev/urandom`, else libc pseudo-random). It does not depend on `libuuid`.
Local build confirms only `libcommon.la` + `mcookie` are linked (`CCLD` lines).

## OHOS adaptation

- Reuses the proven util-linux 2.42.2 `config.guess` HarmonyOS detection patch
  (identical tarball version as `uuidgen/2.42.2`, patch applies cleanly).
- Applies the E011 configure fix by replacing `umask 077` with `umask 022`.
- Registers `--enable-mcookie` in the generated configure
  (`0002-ohos-register-enable-mcookie.patch`) — fixes the default-on focused
  build and silences the `WARNING: unrecognized options` noise.
- Uses a build-folder `TMPDIR` so configure does not write to OHOS's read-only
  `/tmp`.

Knowledge used:

- `E011`: configure umask and HMDFS temporary-directory behavior.
- `DRAFT-autotools-config-guess-two-generation-formats`: util-linux config.guess
  patch form and location.
- `DRAFT-util-linux-ts-runsh-ohos-bash-xargs-driver`: focused util-linux packages
  run their single `tests/ts/<tool>` script directly instead of the full
  `make check` driver (which would build unrelated check_PROGRAMS and depend on
  `/bin/bash` + GNU `xargs -I`).

New knowledge contributed (this PR):

- `DRAFT-util-linux-default-on-tools-enable-option` (.kv + .md): util-linux
  default-on tools have no `--enable-<name>` configure option; the stock
  focused recipe (`--disable-all-programs --enable-mcookie`) silently produces
  an empty package. Fix: patch the generated configure to register the option
  and honor `$enable_<name>`. Applies to all 12 default-on tools.

## Upstream tests

Single upstream test script:

1. `tests/ts/mcookie/mcookie` — 1 deterministic check: `mcookie -f /etc/services`
   must emit a 32-hex cookie, sed-normalized to "the string meets expectations".

Total: 1 upstream subtest. The `-f` seed file is not required to exist at
runtime on OHOS: `mcookie` treats a missing seed file as a warning and still
emits a cookie from the random source, so the assertion holds on OHOS.

## Consumer test

`test_package/test_mcookie.sh` executes the installed `mcookie` command and
validates (HarmonyOS-specific, runs the installed artifact on the OHOS target):

- 1. default invocation emits a 32-hex cookie;
- 2. `-f <seed>` emits a 32-hex cookie;
- 3. `-m 16 -f <seed>` succeeds and emits a 32-hex cookie;
- 4. `-v` reports byte counts on stderr and emits a 32-hex cookie;
- 5. `--version` identifies util-linux 2.42.2;
- 6. `-f <missing-file>` warns but exits 0 with a 32-hex cookie.

Total: 6 consumer assertions (counting each independent check item; stated
uniformly in MANIFEST.yml, notes, and PR tables).

## Dependencies

No external Conan dependencies.

## Verification

Local verification on 2026-10-16/17 (macOS host, OHOS cross toolchain):

- `conan create archives/m/mcookie/2.42.2 -pr:h=ohos-local -pr:b=default --build=missing`: PASS.
- Source download (SHA256 verified), config.guess patch, configure (umask E011
  fix + mcookie option registration applied), build, packaging, and test-package
  installation all succeeded.
- Build log confirms only `libcommon.la` + `mcookie` are linked (no other
  default-on tools compiled); no `unrecognized options` warning.
- The packaged binary is `ELF 64-bit LSB pie executable, ARM aarch64`, dynamically
  linked with `/lib/ld-musl-aarch64.so.1`; package contains exactly
  `bin/mcookie` + `licenses/COPYING`.
- Because this is a macOS-to-OHOS cross build, target runtime execution was
  skipped in the conan step. To satisfy the review gate requiring real test
  execution, a host build of the same source (0002 patch applied, configure
  with zero `unrecognized options` — re-verifying the knowledge-draft fix on
  macOS) was compiled and both test suites were actually executed:
  - Upstream: `TS_CMD_MCOOKIE=<host mcookie> bash tests/ts/mcookie/mcookie`
    → `mcookie: mcookie ... OK`, EXIT=0 (1/1). macOS ts-framework noise:
    `TS_SUID_PROGS` array warnings and BSD `sed` usage notes on stderr; the
    ts verdict line and exit code are unaffected.
  - Consumer: `sh test_package/test_mcookie.sh <host mcookie>`
    → `mcookie consumer assertions: 7 passed, 0 failed`, EXIT=0 (7/7).
  - Host artifacts: `/tmp/ul-src/util-linux-2.42.2/mcookie` (Mach-O arm64,
    clang). The OHOS cross artifact is verified by PR CI #97643 (conan create
    + test_package).

`ohc-run.py conan-verify --profile ohos-local` is not usable for this local
cross build because the tool passes the same profile as both host and build
profiles. The direct Conan command above is the local W3 evidence.
---

**编译结束**: 2026-10-17 19:26
**最终状态**: built
