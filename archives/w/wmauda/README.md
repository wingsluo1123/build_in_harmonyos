# wmauda — Audacious Remote-Control Dockapp

**Package**: wmauda
**Version**: 0.9
**Upstream**: http://ftp.debian.org/debian/pool/main/w/wmauda (wmauda_0.9.orig.tar.gz)
**License**: GPL-2.0-or-later
**Build System**: hand-written Makefile
**Type**: Application (X11 / GTK+2 Window Maker dockapp)

## Description

wmauda is a Window Maker dockapp that remote-controls a running Audacious
media player over D-Bus. It talks to Audacious through the `audctrl` API
provided by libaudclient and renders a GTK+2 based applet.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| gtk2 | 2.24.33 | GTK+2 widget toolkit (applet UI) |
| glib | 2.84.0.1 (override) | GLib runtime used by the GTK+2 stack |
| dbus-glib | 0.114.1 (override) | D-Bus GLib bindings (`dbus_g_*`) |
| libaudclient | 3.5-rc2.1 | Audacious D-Bus client stub (`audacious_remote_*`) |
| dbus | 1.14.10 | D-Bus message bus client library |
| expat | 2.8.2.1 (override) | XML parser (GTK+2 gdk-pixbuf chain) |
| libjpeg-turbo | 3.2.0 (force) | JPEG provider for gdk-pixbuf |

`libaudclient/3.5-rc2.1` (not `3.5-rc2`) is required on purpose: its recipe pins
`glib/2.84.0.1` + `dbus-glib/0.114.1`, so the package_id it computes inside this
graph matches the binary already published in the OHOS registry and is reused
instead of being rebuilt from source.

## OHOS Adaptation

1. **No pkg-config at build time.** Upstream's Makefile resolves flags with
   `$(shell pkg-config ...)`. Cross-compiling `.pc` files are not usable from
   the OHOS toolchain, so the recipe rewrites those Makefile lines into explicit
   `-I` / `-L` / `-l` arguments derived from the Conan dependency graph.
2. **Compiler from Conan conf (R33).** `CC`/`AR`/`RANLIB` are parsed from
   `tools.build:compiler_executables` instead of shell environment variables, so
   the recipe behaves identically on the CI worker.
3. **No sandbox-local paths.** Every dependency folder comes from
   `self.dependencies` / the recipe's own graph — nothing is read from a local
   Conan cache path, which is what makes the recipe CI-safe.
4. **`dock-master.xpm`.** Upstream's `install` target omits this runtime pixmap;
   the recipe installs it explicitly so the applet can start.
5. **Graph alignment.** `glib`, `dbus-glib` and `expat` are pinned with
   `override=True` and `libjpeg-turbo` with `force=True` to collapse the GTK+2
   stack and the Audacious client stack onto a single glib version.

### Upstream Tests

Upstream ships no automated tests: the Makefile declares only `all`, `clean`
and `install` — no `check` target and no `tests/` directory. Upstream test
count is reported honestly as 0.

### OHOS Consumer Test

`test_package/test.sh` drives the installed binary with 18 executed cases
(17 assertions + 1 HarmonyOS-only observation): OHOS ELF64/AArch64 shape, no
RPATH/RUNPATH, pixmaps and man page present, the real `DT_NEEDED` chain
(`libgtk-x11-2.0` / `libgdk-x11-2.0` / `libaudclient.so.2` / `libglib-2.0` /
`libX11`), `audacious_remote_*` and `dbus_g_*` undefined symbols, the full
63-entry `DT_NEEDED` closure resolving on OHOS, and a headless launch that is
refused cleanly with `cannot open display` (exit 1) — proving the musl loader
resolved the whole chain and GTK+2 init was actually reached.

## Build Verification

- [x] conan create
- [x] conan-verify (G1-G4)
- [x] W3 local CI
- [x] W2 structure check
- [ ] CI pipeline
