# spice-gtk 0.42 OpenHarmony PC adaptation notes

## Scope

This first recipe builds the core `libspice-client-glib-2.0` and
`libspice-client-gtk-3.0` libraries plus the installed `spicy`,
`spicy-screenshot`, and `spicy-stats` tools.

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

The `test_package` compiles a C consumer against the installed headers/libs and
checks version string access, debug flag toggling, `SpiceSession` construction,
and the GTK display type registration.

## Local CI precheck

2026-07-27 local precheck used the OHOS-adapted Conan 2.29.1 from the
OpenHarmony community PyPI source in an isolated workspace `CONAN_HOME`.

Results:

- Python syntax check passed for `conanfile.py` and
  `test_package/conanfile.py`.
- `git diff --check` passed.
- `conan create` reached recipe export and dependency graph resolution.
- Fixed during precheck: replaced unavailable `conan.tools.meson.meson_layout`
  with `conan.tools.layout.basic_layout`, matching other Meson recipes in this
  repository and Conan 2.29.1.
- Current blocker: dependency resolution stops at `json-glib/1.6.6` because the
  `ohpcd` Conan remote reports it unavailable. Build, upstream tests, and
  `test_package` execution are therefore not reached locally.

Test-rate claim from this precheck: upstream tests 0/5 executed, added
`test_package` tests 0/1 executed. Do not claim passing rates until the missing
dependency is published or the dependency reference is corrected and
`conan create` completes locally.
