# scanbd

Scanner button daemon: watches SANE scanners, and runs the action scripts configured in
`scanbd.conf` when a scanner button is pressed. Ships the `scanbm` compatibility entry.

## Homepage
https://sourceforge.net/projects/scanbd/

## License
GPL-2.0-or-later

## Build System
Autotools (bundled `configure` + `make`)

## Dependencies
- libconfuse — `scanbd.conf` parsing
- sane-backends (libsane) — scanner back ends
- dbus (libdbus) — D-Bus interfaces used by `scanbm`

## OHOS Adaptation
- `config.sub` does not know the `aarch64-linux-ohos` triplet — patched (`patches/0001`)
- `config.status` creates its temp directory with `mktemp -d` (mode 0700), which HMDFS
  projects as an unwritable directory — patched to `mkdir` (`patches/0002`, E114/E046)
- OHOS libc has no `pthread_cancel` / `pthread_testcancel` / `pthread_setcancelstate` —
  `dbus.c` and `sane.c` use cooperative stop flags instead (`patches/0003`)
- Dependency `*.la` files record build-machine paths (`libdir='//lib'`,
  `dependency_libs='//lib/libpng16.la'`), which breaks libtool at link time — the recipe
  stages rewritten copies and prepends them to the pkg-config `Libs:` search path
- `AC_FUNC_MALLOC` cannot run its probe while cross-compiling and redirects `malloc` to
  gnulib's `rpl_malloc()`, which OHOS does not provide — `ac_cv_func_malloc_0_nonnull=yes`
- Upstream's `noinst_DATA` rules read `$@.in` outside `$(srcdir)`, so only in-tree builds
  work — patched for out-of-tree builds (`patches/0004`)
- udev and HAL are disabled (`--disable-udev --disable-hal`); scanbd then uses its
  SIGHUP-based polling path

## Versions
- 1.5.1 — built 2026-10-03 (upstream has no automated tests; 4/4 consumer checks pass)
