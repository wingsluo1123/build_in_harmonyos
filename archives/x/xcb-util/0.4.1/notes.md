# xcb-util 0.4.1 adaptation notes

## Source and scope

Official X.Org release archive:
`https://www.x.org/archive/individual/lib/xcb-util-0.4.1.tar.gz`, SHA-256
`21c6e720162858f15fe686cef833cf96a3e2a79875f84007d76f6d00417f593a`
(byte-identical to `xorg.freedesktop.org/archive/individual/lib/...` — www.x.org
is a redirect alias of the same archive tree, and the file matches both the
xorg-announce 2022-December posting and the git tag `xcb-util-0.4.1`, commit
`3a157762`, GPG verified). The release tarball ships pre-generated `configure`
and `Makefile.in`, so no autoreconf/automake step is needed — mandatory on the
OHOS device, which has neither automake nor libtool installed.

The package is the xcb-util family root: since 0.3.8 the former atom, aux and
event helpers are a **single** library `libxcb-util` (version-info 1:0:0 →
`libxcb-util.so.1`, sources `atoms.c`/`event.c`/`xcb_aux.c`), installed into
`include/xcb/` with four headers (`xcb_util.h`, `xcb_atom.h`, `xcb_aux.h`,
`xcb_event.h`) and four pkg-config files (`xcb-util.pc` plus the historical
`xcb-aux`/`xcb-atom`/`xcb-event` aliases) that all resolve to the same library.

## Dependency closure

Only `libxcb/1.17.0` is required (same as xcb-util-wm/0.4.2). No xorgproto
require, unlike xcb-util-wm: `src/` includes no `X11/` header at all — the only
external header is `<xcb/xcb.h>` and the only linked library is libxcb. xcb-proto
is not a direct dependency either; xcb-util merely *checks* (not runs) the
xcb-proto version that libxcb was generated from.

## Notable adaptation issues (same fixes as xcb-util-wm/0.4.2)

- **xcbproto_version in xcb.pc**: `XCB_UTIL_COMMON` runs
  `pkg-config --variable=xcbproto_version xcb` and aborts if < 1.6. Conan's
  minimal generated `xcb.pc` lacks the variable, so `generate()` copies the
  `xcbproto_version=` line from the real `xcb.pc` shipped inside the libxcb
  package (isfile-guarded).
- **HMDFS umask / shebang**: the generated `configure` carries `umask 077`
  (config.status creates directories even the owner cannot write on HMDFS) and
  `#! /bin/sh` shebangs that /system/bin/sh cannot run; `build()` rewrites both
  (`umask 022`, `#!/data/service/hnp/bin/bash`) on OHOS only.
- **Stale dependency .la paths**: dependency `.la` files from the libxcb
  package get their `libdir` rewritten to the consumer copy and bare `.la`
  references become `-l<name>`; the package's own installed `.la` gets its
  `libdir` rewritten to the package folder after install.
- **Explicit link closure** (implement-policy item 5): `libxcb-util.so` resolves
  libxcb symbols, so `generate()` appends `-L<libxcb libdir>` and
  `-Wl,-rpath-link,<libxcb libdir>` to the toolchain LDFLAGS before the
  environment snapshot, guarded by the presence of `libxcb.so`; no reliance on
  implicit lld DT_NEEDED closure search.

## Build behavior

Autotools with `--build/--host=aarch64-unknown-linux-gnu`, shared linking only.
`make check` is invoked even though the release ships no test programs (no
`tests/` directory, no `TESTS`/`check_PROGRAMS` in `src/Makefile.am`), so the
build log carries a trace of the upstream check target.

## Validation

Two ctest-driven consumer binaries run in `test_package`, both without an X
server (knowledge entry E530: X11-family client libraries ship no upstream
tests and OHOS CI workers have no Xvfb):

- `test.c` (generic consumer test): strong-typed relocation of the exported
  symbols, `_Static_assert` + `offsetof` pins of all four `xcb_params_*`
  packing structs, then real calls of the pure helpers — `xcb_aux_parse_color`
  (valid and invalid inputs), the `xcb_event_get_{label,error_label,request_label}`
  lookup tables (including out-of-range NULL), the vasprintf-based
  `xcb_atom_name_*` builders (exercises the musl `HAVE_VASPRINTF` config path),
  and the `XCB_AUX_ADD_PARAM` mask bookkeeping.
- `test_ohos_port.c` (**OHOS-specific**, new in this run): asserts (1) the
  `__OHOS__` toolchain guard is active for this build, (2) the loaded library is
  the versioned soname `libxcb-util.so.1`, located through the loader's own
  bookkeeping (`dl_iterate_phdr`; load-bearing because the OHOS loader ignores
  DT_RUNPATH), (3) the ELF `DT_NEEDED` entries of the shipped library — parsed
  from the file on disk — name the direct dependency `libxcb.so.1` (the
  dependency wired through the recipe's explicit `-L`/`-Wl,-rpath-link`
  closure) and are all bare sonames, never absolute or `../` paths, while the
  toolchain-owned transitive set (`libXau`/`libXdmcp`/`libc`, identical to the
  published `xcb-util-wm/0.4.2` libraries) is deliberately not over-pinned,
  and (4) `libxcb.so.1`/`xcb_connect` resolves at runtime through the same
  environment.

Both are executed by `ctest` from `test()` under the conanrun environment, so
they are actually run (and counted) rather than merely compiled.

---

**编译结束**: 2026-10-16
**最终状态**: built
