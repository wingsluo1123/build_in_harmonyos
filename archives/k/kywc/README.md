# kywc

Kylin Wayland compositor client library (`libkywc`), extracted from the
kylin-wayland-compositor project. It exposes the `kywc_context` API and the
kywc-output / kywc-toplevel / kywc-workspace / kywc-capture manager client
protocol wrappers used by UKUI clients — in this repository, by
`ukui-quick`'s `window-thumbnail` module (`pkg_check_modules(kywc REQUIRED)`,
`#include <libkywc.h>`).

## OHOS adaptation

- Only `libkywc` is built. The compositor stack that normally ships with it
  (wlroots 0.20, xkbcommon, libdrm, libinput, libdisplay-info, pixman,
  cairo/pango, librsvg, libsystemd, json-c, udev, gbm) is not packaged for
  OHOS. Three local patches add a `compositor` option (default true) that
  gates every compositor-side target while leaving `protocols/` and
  `libkywc/` unconditional; with `-Dcompositor=false` the remaining
  requirements are wayland-client, wayland-protocols and libm.
- The `wayland-scanner` used by `protocols/meson.build` is compiled
  statically from wayland 1.24.0 source, because HMDFS refuses to execute
  cache binaries that link shared libraries (same approach as
  wayland-protocols/1.48).
- A hand-written `wayland-protocols.pc` exposes the `pkgdatadir` variable
  that `protocols/meson.build` reads through `get_variable()`.
- Installed ELFs are re-signed after `meson install` (install rewrites the
  RUNPATH and invalidates the link-time `.codesign` section), and the
  `libkywc.so.1` / `libkywc.so` links are restored if the install lost them.

## Dependencies

- Required at build and runtime: wayland >= 1.24.0, wayland-protocols >= 1.36
- Build system: Meson

## Versions

- 1.3.2: initial adaptation (2026-10-20), Debian pool orig tarball; upstream
  gitee only publishes 1.3.0/1.3.1 tags.
