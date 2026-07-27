# spice-gtk 0.42 OpenHarmony PC adaptation notes

## Scope

This first recipe defaults to the validated GLib client package: it builds
`libspice-client-glib-2.0` plus the installed `spicy-screenshot` and
`spicy-stats` tools. GTK UI support remains available behind the `gtk` option,
but is disabled by default until `gtk+/3.24.38` is available in the dependency
set and can be validated locally.

The following optional stacks are disabled for the first cross-platform package:
WebDAV/phodav/libsoup, USB redirection, USB ACL helper/libcap-ng/polkit, SASL,
Opus, smartcard/cacard, Wayland protocol generation, EGL, introspection, VAPI,
gtk-doc, translations, and man pages.

## High-difficulty evidence

`spice-gtk` is tightly coupled to desktop/session infrastructure and remote
display paths. The source tree binds together GTK/GDK, GLib/GIO, GStreamer
video/audio pipelines, SPICE protocol code generators, optional Wayland/X11
window handles, USB redirection, WebDAV file transfer, SASL authentication, and
smart-card support. Full validation normally requires a live SPICE server and
desktop/display/audio/USB integration, which is outside a simple compile-only
test environment.

## Test counting

Upstream `tests/meson.build` registers 5 base tests in the selected no-WebDAV,
no-USB, no-polkit scope: `test-util`, `test-coroutine`, `test-session`,
`test-uri`, and `test-file-transfer`. The recipe disables the upstream test
subdir during cross packaging and supplies a Conan consumer test instead.

The `test_package` compiles a C consumer against the installed headers/libs. In
the default `gtk=False` package it checks version string access, debug flag
toggling, and `SpiceSession` construction. The GTK display type registration
check is compiled only when the `gtk` option is enabled.

## Local CI precheck

2026-07-28 local precheck used the OHOS-adapted Conan 2.29.1 from the
OpenHarmony community PyPI source on a real HarmonyOS PC remote environment.

Results:

- Python syntax check passed for `conanfile.py` and
  `test_package/conanfile.py`.
- `git diff --check` passed.
- `conan create archives/s/spice-gtk/0.42 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 -o spice-gtk/*:gtk=False
  --build=missing --build=spice-gtk/*` completed on commit `ca8873096`.
- Fixed during precheck: replaced unavailable `conan.tools.meson.meson_layout`
  with `conan.tools.layout.basic_layout`, matching other Meson recipes in this
  repository and Conan 2.29.1.
- Dependency graph resolved through `json-glib/1.6.6`, `gstreamer/1.28.3`, and
  `gst-plugins-base/1.28.3`.
- Meson configure/build completed 69/69 build steps, packaged
  `libspice-client-glib-2.0.so.8.8.2`, installed a copied SONAME file for OHOS
  symlink limitations, and installed `spicy-screenshot`/`spicy-stats`.
- `test_package` compiled and linked the C consumer test on OHOS. Runtime
  execution is explicitly skipped on OHOS because the dynamic loader does not
  reliably load shared libraries from Conan cache/test paths.

Test-rate claim from this precheck: upstream tests 0/5 executed, added
`test_package` compile/link tests 1/1 passed. Do not claim runtime smoke
execution passed on OHOS.
