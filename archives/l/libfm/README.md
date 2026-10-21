# libfm — GLib-based Library for File Managers

**Package**: libfm
**Version**: 1.4.0
**Upstream**: https://github.com/lxde/libfm
**License**: LGPL-2.1
**Build System**: CMake (hand-written; upstream tarball ships autotools only)
**Type**: Library (full core + libfm-extra sub-library; no GTK parts)

## Description

libfm is a GLib/GIO-based library providing file-management facilities for
desktop file managers (PCManFM et al.). This archive ships the **full libfm
core library** (`libfm.so.4` — base + job + extra components, equivalent to
upstream `libfm.la` without the GTK-dependent parts) plus the standalone
**libfm-extra** sub-library (`FmXmlFile` XML parser). GTK-dependent
components (libfm-gtk, src/demo), modules/, udisks, dbus and exif optional
features are out of scope (PC HarmonyOS has no GTK stack).

Deliverables (per version):

- `lib/libfm.so.4.0.2` (SONAME `libfm.so.4`; exports glib symbols so
  consumers share a single glib instance)
- `lib/libfm-extra.so.4.1.3` (SONAME `libfm-extra.so.4`, self-contained)
- `include/libfm-4/{fm.h, fm-seal.h, base/*.h, job/*.h, fm-marshal.h,
  fm-extra.h, fm-xml-file.h, fm-version.h}` (flat layout, upstream parity)
- `lib/pkgconfig/{libfm.pc, libfm-extra.pc}`

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| glib | 2.88.0 | GObject/GIO/GThread/GModule (linked into libfm.so, symbols exported) |
| pcre2 | 10.45 | glib transitive dep (libpcre2-8, hidden into the .so) |
| zlib | 1.3.1 | glib transitive dep (libz, hidden into the .so) |
| menu-cache | 1.1.0 | fm-file-info.c requires menu-cache.h (hidden into the .so) |

Runtime `NEEDED` of both `.so` files is `libc.so` only; non-GType deps are
statically closed and hidden, glib-family symbols are exported by
`libfm.so.4` so consumers linking `-lfm` share the single glib instance.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.3.2 | published | (pre-existing archive) |
| 1.4.0 | published | full core + libfm-extra; OHOS aarch64 |

## Notes

- Upstream tests: `src/tests/test-fm-path.c` and
  `src/tests/libfm-file-search-cli-demo.c` are really executed in
  test_package (PASS). `src/demo/libfm-demo.c` and `src/gtk/exo/test.c`
  require GTK3 — not executable on PC HarmonyOS (see `1.4.0/notes.md`,
  R51 inventory).
- E529: statically linking glib requires explicit transitive link deps
  (pcre2/zlib/ffi/intl/m); missing them only fails at `dlopen` relocation
  time, not at link time.
- E530: non-PIC static archives (conan zlib/pcre2 etc.) must be hidden via
  `--exclude-libs` when linked into a shared object.
- E531: never split the glib instance — hiding glib symbols inside the .so
  while consumers link their own static glib breaks the GType system
  (GObject signals resolve against '(null)' types).
