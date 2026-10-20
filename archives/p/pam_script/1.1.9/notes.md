# pam_script 1.1.9 adaptation notes

## Scope

- Task: DEP #15853, branch `feat/pam_script-1.1.9`
- Upstream: https://github.com/jeroennijhof/pam_script, tag `1.1.9`
- Source: `https://codeload.github.com/jeroennijhof/pam_script/tar.gz/refs/tags/1.1.9`
  (`pam_script-1.1.9.tar.gz`, sha256
  `0aab103d318e3048ccc6f8285950f99284c814f996d2dcbcae8f10d3b8bd8cfe`)
- Edit scope: `archives/p/pam_script/1.1.9/` only

## What the library is

A loadable PAM module. For each module type it forks and execs one script
(`pam_script_auth`, `pam_script_acct`, `pam_script_passwd`,
`pam_script_ses_open`, `pam_script_ses_close`), exports the PAM items as
environment variables, and maps the script exit status onto the PAM return
code. `onerr=success|fail` and `dir=/path` are the only options.

The hard dependency is a PAM implementation. `linux-pam/1.7.2` is already
published in the ohpcd remote and provides `<security/pam_appl.h>`,
`<security/pam_modules.h>`, `libpam.so`, `libpam_misc.so`.

## Upstream test inventory: 0 cases

The 1.1.9 tag archive contains `pam_script.c`, the autotools files,
`pam-script.7.in`, `etc/` examples and packaging files. There is no `tests/`
directory, no `check` target in `Makefile.am`, and `.travis.yml` only runs
`autoreconf -i && ./configure && make`.

```
$ tar tzf pam_script-1.1.9.tar.gz | grep -iE 'test|check' ; echo "count=$?"
count=1        # no match
$ grep -n 'check' Makefile.am   # only `help:`/`distclean` text
```

So the upstream count is 0/0 and the whole verification weight is on the
OpenHarmony specific consumer test (18 assertions).

## Build system: autotools is not usable on OHOS, CMake glue instead

Upstream ships `configure.ac` only; the GitHub archive has no generated
`configure`, so `autoreconf -fi` is required. The repository convention for
that is `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`.
On the device that fails before any upstream source is compiled:

```
RUN: autoreconf -fi
.../p/autom3efab95d532f9/p/bin/aclocal[8]: .../p/bin/.aclocal-real: No such file or directory
autoreconf: error: .../p/bin/aclocal failed with exit status: 126
```

Root cause: the published `automake/1.18` package wraps `bin/aclocal` around
`bin/.aclocal-real`, whose shebang is `#!/data/service/hnp/bin/perl`. That
interpreter does not exist on the device (perl lives in
`~/.harmonybrew/bin/perl`), so the exec fails with ENOENT. In addition the
autotools route needs the HMDFS `config.status` umask workaround
(`umask 077 && mktemp -d` is not writable on HMDFS, see
`archives/a/adplay/1.9`).

The whole upstream build is one translation unit linked as a version-less
libtool module, so the recipe reproduces exactly that artifact with CMake,
which both the OHOS toolchain and the repository CI already provide:

```
libtool -module -avoid-version pam_script.la  ->  lib/security/pam_script.so
```

The recipe writes a 30 line `CMakeLists.txt` into the exported source folder
and passes the feature macros `configure` would otherwise generate:
`PACKAGE="pam-script"`, `HAVE_SETENV=1`, `HAVE_VSYSLOG=1` and
`PAM_SCRIPT_DIR="/etc"` (the `$(sysconfdir)` default from `Makefile.am`).
`HAVE_CONFIG_H` stays undefined, so `pam_script.c` does not include
`config.h`. No upstream source file is modified.

`make install` is not reproduced: upstream's install hooks create symlinks in
`${sysconfdir}` and run the `etc/pam_script` helper, which is a system
administration step. The package ships the module, the man page (rendered from
`pam-script.7.in`), the upstream `etc/README*` documentation and `COPYING`.

## OHOS specific findings

1. **dlopen()ed modules only resolve symbols inside their own dependency
   closure.** With `pam_*` left undefined (the normal PAM module layout), the
   consumer test failed with

   ```
   dlopen error: Error relocating .../lib/security/pam_script.so:
   pam_get_user: symbol not found
   ```

   even though the test program links `libpam.so.0` and has it loaded. The
   recipe therefore records `DT_NEEDED libpam.so.0` explicitly
   (`target_link_libraries(pam_script PRIVATE ${PAM_LIBRARY})`). The host PAM
   stack already has the same DSO loaded, so no second copy appears at
   runtime; `readelf -d` shows `NEEDED libpam.so.0` + `NEEDED libc.so`.

2. **`binary-sign-tool` is not on `PATH`.** It ships in the OHOS SDK at
   `~/.harmonybrew/opt/ohos-sdk@26.0.0.18/bin/binary-sign-tool`, not in
   `/data/service/hnp/bin`. `_find_ohos_tool()` therefore probes
   `$OHOS_BINARY_SIGN_TOOL`, `$SIGN_TOOL_PATH`, `/data/service/hnp/bin`, the
   `tools.build:compiler_executables` directory, `~/.harmonybrew/opt/ohos-sdk*/bin`
   and finally `PATH`. The packaged module carries a `.codesign` section.

3. **`PAM_SCRIPT_DIR` ownership gate cannot be exercised as a non-root user.**
   Upstream `check_path_perms()` requires the script and its directory to be
   owned by `root:root` and to be fully executable, so a Conan consumer test
   can never reach the fork/exec branch. The consumer test drives the same
   code path up to that gate and verifies the documented `onerr=` mapping
   instead (see below).

## Consumer test (OpenHarmony specific, 18 assertions)

`test_package/test_pam_script.c` dlopen()s the installed
`lib/security/pam_script.so`, resolves all six `pam_sm_*` entry points, and
drives the module through a real linux-pam stack:

- `pam_start_confdir()` with a private configuration directory (the device has
  no `/etc/pam.d`, so `pam_start()` cannot be used),
- service `pam15853ok`: `auth/account required <module> onerr=success dir=<dir>`
  -> `pam_authenticate()` returns `PAM_SUCCESS`, the conversation callback is
  called exactly once with the upstream `"Password: "` prompt,
  `pam_setcred()` returns `PAM_SUCCESS`, `pam_acct_mgmt()` returns
  `PAM_SUCCESS`, `pam_end()` returns `PAM_SUCCESS`,
- service `pam15853fail`: same stack without `onerr=success` (the upstream
  default) -> `pam_authenticate()` returns `PAM_AUTH_ERR`, again after exactly
  one `"Password: "` conversation.

## Real-device verification

- Device: OHOS 6.0, aarch64, Conan 2.29.1, profile `ohos-aarch64` for both
  `-pr:h` and `-pr:b`, `--build=missing --conf tools.build:jobs=2`
- Command: `conan create archives/p/pam_script/1.1.9 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --conf tools.build:jobs=2`
- Result: exit code 0, `PAM-SCRIPT-CONSUMER-SUMMARY total=18 pass=18 fail=0`
- Package: `pam_script/1.1.9#...:4bca52c9852602366f898d595f49b9c3a9620483`,
  package revision `3d318a2e88a3c0afa724dd13379902b8`
- Log: `/storage/Users/currentUser/work/psj/pam15853/output/pam15853-create-r6.log`,
  sha256 `7c5731953e5cf9e5196492e9b1465731c72cd071a7a266a21d89ac89b4b19dec`
- Payload that produced the log:
  `pam15853-package.tar.gz` md5 `b47fc318a1135e80b8c7ddede67e7e8c`
  (device copy md5-verified before the run)

Intermediate rounds that shaped the final recipe:

| round | outcome |
|---|---|
| r1 | `autoreconf -fi` aborted: `automake/1.18` `bin/.aclocal-real` shebang `#!/data/service/hnp/bin/perl` missing (exit 126) |
| r2 | CMake build ok; `security/pam_appl.h` not found (missing include injection) |
| r3 | module built, signed, packaged; consumer `dlopen` failed with `pam_get_user: symbol not found` |
| r4 | module linked against `libpam.so` -> 18/18 consumer assertions pass |
| r5 | uploaded payload was stale (ssh timeout), discarded |
| r6 | final recipe, exit code 0, 18/18 |

## Package layout

```
lib/security/pam_script.so        (signed)
share/man/man7/pam-script.7
share/doc/pam_script/README*
licenses/COPYING, licenses/README
```

`package_info()` exposes no linkable library (a PAM module is dlopen()ed),
sets `cmake_file_name`/`cmake_target_name` to `pam_script`, declares
`cpp_info.requires = ["linux-pam::pam"]`, and publishes
`PAM_SCRIPT_MODULE` plus `LD_LIBRARY_PATH` in `runenv_info`.

## Known limits

- The fork/exec branch (`pam_script_auth` and friends) is not exercised: it is
  gated on `root:root` ownership of the script directory, which is not
  reachable from an unprivileged Conan consumer test.
- The module is not registered in a system PAM stack. OpenHarmony does not use
  Linux-PAM for console login, so the package is a library/plugin artifact for
  consumers such as `pam-wrapper`, `pam-u2f` or `pam-reattach`, not a
  drop-in login hook.
