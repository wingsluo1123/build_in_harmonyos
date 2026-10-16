# kio-fuse

kio-fuse exposes KIO URLs (remote, archive, ...) as a real userspace FUSE
filesystem: the `kio-fuse` daemon (a libexec helper, D-Bus activated as
`org.kde.KIOFuse`) mounts a kernel FUSE filesystem and serves the file I/O
through KF6::KIOCore (KIO::FileJob or the FIO worker). The package ships
the daemon, the org.kde.KIOFuse D-Bus activation service file and the
kio-fuse systemd user unit.

## OHOS adaptation

- Qt6::DBus is wired in with two minimal source patches: the OHOS
  kio/6.26.0 is built with `USE_DBUS=OFF`, so its KF6KIO config exports no
  transitive Qt6DBus link, and the versionless `Qt::DBus` alias must be
  created in a directory scope `src/` can see. The module itself comes
  from qtbase-sql-dbus/6.11.1 (qtbase/6.11.1 ships `FEATURE_dbus=OFF`).
- libfuse/3.18.2 links statically: a shared libfuse3 would need the
  meson symlink chain (libfuse3.so -> libfuse3.so.3.x), which the OHOS
  HMDFS sandbox rejects (`symlink()` EPERM), and the static archive keeps
  the daemon self-contained. A hand-written `fuse3.pc` is placed in the
  generators folder because upstream sources use plain
  `#include <fuse_lowlevel.h>` while a dependency-generated `.pc` exposes
  a bare `-I${includedir}`.
- A shared `libdbus-1.so.3` is vendored from the official dbus 1.14.10
  sources inside the recipe: the OHOS qtbase builds Qt6DBus with
  dbus-linked=OFF, so `libQt6DBus` dlopen()s `libdbus-1.so.3` at runtime
  while the registry only publishes a static `libdbus-1.a`. The version
  chain is completed with file copies (the sandbox denies `symlink()`).
- `KDE_INSTALL_LIBEXECDIR` is pinned to `libexec`: ECM's UNIX check fails
  under the device `CMAKE_SYSTEM_NAME`, which would otherwise install the
  daemon into `bin/`, breaking the D-Bus service file and systemd unit.
- Absolute `DT_NEEDED` entries are rewritten with patchelf after linking:
  the platform kcoreaddons/6.26.0 package ships its library without a
  `DT_SONAME`, so linking its imported target records the build machine's
  cache path as an absolute entry. The rewritten bare name resolves via
  `LD_LIBRARY_PATH` like the rest of the dependency set.
- The packaged ELF tree is re-signed after `cmake.install` (RUNPATH
  rewrite invalidates the toolchain `.codesign` section; the kernel then
  refuses to exec the daemon).
- The two upstream fileopstests are excluded from the ctest run: kernel
  FUSE mounts are denied by the OHOS app sandbox (`open("/dev/fuse")` ->
  EACCES, `mount(2)` -> SIGSYS) and `dbus-run-session` is unavailable.
  They still compile with `BUILD_TESTING=ON` (Qt6Test/Qt6DBus and
  qt_add_dbus_interface exercised at build level).

## Dependencies

| Dependency | Purpose |
|---|---|
| qtbase-sql-dbus/6.11.1 | Qt6 Core/Network/DBus/Test (dbus-enabled qtbase build) |
| kio/6.26.0 | KF6::KIOCore — the KIO job machinery behind the filesystem |
| kcoreaddons/6.26.0 | KF6::CoreAddons (KProcess, plugin metadata) |
| libxml2/2.15.3 | libxml2.so.16 SONAME resolution for the OHOS SDK lld link |
| libfuse/3.18.2 | FUSE 3 userspace library (static; HarmonyOS portability patches) |
| (vendored dbus 1.14.10) | `libdbus-1.so.3` for the Qt6DBus dlopen at runtime |

## Reference

- Upstream: https://invent.kde.org/system/kio-fuse
- Source release: https://download.kde.org/stable/kio-fuse/kio-fuse-5.1.1.tar.xz
