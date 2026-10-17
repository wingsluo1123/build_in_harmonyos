# otpclient

OTPClient is a TOTP/HOTP one-time-password manager for Linux desktops. It stores
secrets in the system keyring (libsecret), can import from `andOTP`/`Aegis`/
`FreeOTP+` backups and screenshots, and ships a GTK4/libadwaita GUI, a
`otpclient-cli` command-line front end, and a KRunner/D-Bus search provider.

## OHOS adaptation

- Builds the official 5.1.5 release tarball with CMake ≥ 3.25 and `pkg-config`.
- Keeps upstream sources unchanged except for one portability patch: probe
  `explicit_bzero()` at configure time and fall back to an inline implementation.
  OHOS/musl does not declare it, and upstream compiles with
  `-Werror=implicit-function-declaration`.
- Adds `-D_GNU_SOURCE` (musl hides POSIX declarations such as `struct sigaction`
  that glib/libsecret consumers rely on).
- Links `-lintl` through the glib `.pc` files actually consumed by upstream
  (NLS/gettext symbols such as `g_libintl_gettext` are not in libc on OHOS).
- Normalizes the short glib component names found in published dependency
  `cpp_info` (`glib::gobject` → `glib::gobject-2.0`) on the consumer side, the
  same way `libedataserverui4` does, so `PkgConfigDeps` can emit the `.pc` files
  upstream asks for (`cotp` → `libcotp.pc`, `libqrencode` → `qrencode.pc`).
- Runs the upstream CTest suite (13 unconditional cases; 3 more are GUI-gated)
  plus a consumer test package that executes the packaged CLI and checks the
  installed GSettings schema/desktop data.
- GUI is off by default and kept behind the `gui` option: the GTK4 build needs
  `glib-compile-resources`/`glib-compile-schemas` host tools whose dynamic
  dependencies are not satisfiable from the published dependency chain.

## Dependencies

- `glib/2.84.0.1` — glib-2.0 / gio-2.0 (≥ 2.74.0).
- `libsecret/0.21.7` — libsecret-1 (≥ 0.20.0).
- `libgcrypt/1.11.0` — libgcrypt (≥ 1.10.1).
- `libcotp/4.2.1` — cotp (≥ 4.0.0).
- `jansson/2.15.1.1` — jansson (≥ 2.13).
- `libuuid/2.42.2` — uuid (≥ 2.30.0).

`gui=True` additionally pulls `gtk4`, `libadwaita`, `gdk-pixbuf`, `zbar`,
`protobuf-c` and `qrencode`.

## References

- https://github.com/paolostivanin/OTPClient
- https://github.com/paolostivanin/OTPClient/archive/refs/tags/v5.1.5.tar.gz
