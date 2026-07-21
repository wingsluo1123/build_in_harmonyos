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
