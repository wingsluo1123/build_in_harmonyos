# meterec 0.9.3 adaptation notes

## Upstream

- Project: meterec — console based multi track digital peak meter and
  recorder for JACK, by Fabrice Lebas; hosted at
  https://sourceforge.net/projects/meterec/ (files/meterec-0.9.3.tgz).
  The author's GitHub mirror (fafaman/meterec) stops at tag v0.9 — 0.9.3
  was released through SourceForge (2020-11-13, per the LinuxAudio wiki
  and the distro package metadata).
- `meterec-0.9.3.tgz` (142015 bytes) SHA256:
  `14ed1af1ec74aaa8de9885d9ddbc22cb7d55e3c58f1498d7ed6f53cfb2b48474`.
  Source provenance: SourceForge now rejects token-less direct downloads
  (HTTP 403 / HTML interstitial; its signed `ts=` download tokens are
  short-lived and cannot be committed to a recipe), so conandata.yml
  points at the distribution-maintained copy of the same official
  tarball (Debian pool `meterec_0.9.3.orig.tar.gz`). Cross-verified
  byte-identical on 2026-10-16: SourceForge original (signed-token
  fetch), Debian pool, and Ubuntu pool all yield the same SHA256, and
  the MD5 `521b2a7b452f890442f22e23b12e8ed0` matches the digest
  published in the Ubuntu (jammy) package metadata for 0.9.3.
- License: GPL-2.0-or-later (tarball COPYING is the GPLv2 "or any later
  version" text). This is a CLI application package; license compliance
  is at the consumer's responsibility.
- 0.9.3 is the final official release (upstream last push 2020-11-13).

## Dependencies (from configure.in, verified against the tarball)

- `jack >= 1.9.7` (PKG_CHECK_MODULES) — satisfied by `jack/1.9.22`.
  configure also checks `jack/session.h` (present in the package).
- `sndfile >= 1.0.25` (PKG_CHECK_MODULES) — satisfied by
  `libsndfile/1.2.2` (pkg_config_name "sndfile").
- `libconfig >= 1.3.2` (PKG_CHECK_MODULES) — satisfied by
  `libconfig/1.8.2` (component "c" publishes libconfig.pc).
- `ncurses >= 5.9` (PKG_CHECK_MODULES, with AC_CHECK_LIB(curses)
  fallback) — satisfied by `ncurses/6.6`. The repository ncurses
  package is static-only and publishes the wide library: ncursesw.pc
  (libs formw/menuw/panelw/ncursesw). `ncurses.pc` does not exist in
  the package, so 0001-configure-ncursesw.patch redirects the probe to
  `ncursesw >= 5.9`. ncursesw is the superset ABI: the sources include
  `<curses.h>` (the package ships a compatible curses.h header) and use
  only the basic (non-wide) API, whose symbols all live in
  libncursesw.a.
- libm / libpthread — probed via AC_CHECK_LIB; both exist in the OHOS
  sysroot. `AC_CHECK_LIB([mx], [powf])` falls through to `-lm` (there
  is no libmx), which provides powf.
- `test` (the shipped queue self-test) is also a bin_PROGRAM; it links
  the same dependency set.

## Upstream test suite

The tarball ships one runnable self-test: the `test` binary (test.c),
a deterministic event-queue exercise (add_event / find_first_event /
rm_event / find_rm_events) that prints the queue state after each
mutation. It needs no JACK server and no terminal. There is no
automake `check`/`test` target and no other test machinery.

## Patches

- `0001-configure-ncursesw.patch` (portability, 8 sites in configure):
  `ncurses >= 5.9` → `ncursesw >= 5.9` in the generated PKG_CHECK
  blocks, matching the only .pc the repository ncurses package
  publishes. Nothing else is changed.
- `0002-configure-umask-022.patch` (portability, 2 sites in configure):
  the confstat tmp dir is created with `umask 077`; on the OHOS CI
  filesystem (setgid hmdfs) that makes the dir unwritable. Use umask
  022 (same knowledge point as madplay 0002). Harmless on ext4.
- No config.sub/config.guess patch is needed: the tarball ships
  neither file, and the autoconf 2.59 generated configure falls back
  to accepting the explicitly passed --host/--build verbatim when
  config.sub is absent (verified empirically: configure accepts
  aarch64-unknown-linux-ohos with no config.sub anywhere on the
  system).

## Build notes

- Autotools (autoconf 2.59 / automake 1.9-era, pre-libtool); built with
  `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
  (cross triplet passed explicitly because `uname -s` is "HarmonyOS" on
  the OHOS worker).
- `make -j1`: 2004-era automake fragments; keep the build deterministic.
- `make install` installs bin/meterec, bin/test, bin/meterec-init-conf
  and the man pages. The recipe keeps all three binaries (faithful to
  upstream bin_PROGRAMS/bin_SCRIPTS).
- The tarball ships a pre-generated config.h; configure regenerates it
  (HAVE_W64 / HAVE_VORBIS come from the libsndfile headers).

## test_package design

- Runs the real installed binaries on-device (conanrun env):
  1. `test` (upstream queue self-test): exit 0.
  2. `test` output is fully deterministic: 12 state-dump separator
     lines ("====…") and 20 "queue …" lines, first line
     "queue 1 - type 1 - old 1 - new 1 - buf 1".
  3. `meterec -h`: prints "version 0.9.3" and the usage line.
     Upstream usage() calls exit(1), so the expected status is 1.
  4. `meterec` with no args in a scratch dir: no jackd on device →
     exits non-zero with "Failed to start 'meterec' jack client".
  5. `meterec-init-conf` without args: prints the usage text, exit 1.
  6. `meterec-init-conf testsess` in a scratch dir: creates
     testsess.mrec containing `ports=(` and `version=1;` (with no
     jack server the port map is empty — the script degrades
     gracefully).
- `test` is invoked via its absolute path (dirname of `meterec` on
  PATH) because bare `test` resolves to the shell builtin.
- `meterec-init-conf` is a bash-shebang script; it is executed via
  `sh` so the device's mksh can run it (the script body is POSIX).
