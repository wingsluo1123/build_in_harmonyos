# xhost 1.0.10 HarmonyOS adaptation notes

## Upstream source

- Project: https://gitlab.freedesktop.org/xorg/app/xhost
- Official release archive: https://xorg.freedesktop.org/archive/individual/app/xhost-1.0.10.tar.xz
- Archive size: 137,076 bytes
- SHA-256: `a8afd70059479c712948b895e41c35a4a8bfcede3ba2d5a4b855c88bbb725be1`
- The locally computed digest matches the independent Buildroot `xapp_xhost` hash record.

## Build and platform adaptations

- Uses the release's pre-generated `configure` and `Makefile.in`; no autoreconf tools are needed.
- `configure.ac` requires `xproto >= 7.0.22`, `x11`, `xmuu`, and `xau`; `libxmu/1.3.1.1` supplies libXmuu/libX11/libXau, while `xorgproto/2025.1` is a direct build requirement so its `share/pkgconfig/xproto.pc` is exposed to the root recipe. A first graph run exposed a conflict between libXmu's pinned `libx11/1.8.13` → `libxau/1.0.11` and an unnecessary direct `libxau/1.0.12` requirement; the recipe now follows the matching versions.
- `config.guess` and `config.sub` use the established E205 HarmonyOS triplet fix. The configure scripts use the existing E011/E114 HMDFS-safe umask and PWD handling.
- Conan packages `xproto.pc` in `share/pkgconfig`, so the build adds both `lib/pkgconfig` and `share/pkgconfig` from resolved dependencies to `PKG_CONFIG_PATH`. The published `xmuu.pc` also has a fixed `/usr/local` prefix; the recipe appends actual Conan CppInfo include/lib directories to `CPPFLAGS`/`LDFLAGS`.
- No upstream test directory or registered `TESTS`, `check_PROGRAMS`, or `check_SCRIPTS` exists. The upstream total is 0; `make check` is invoked to record the empty Automake suite. `test_package` executes the installed binary and asserts its usage and no-display behavior.

## Validation

- HarmonyOS 6.0 AArch64 device, Conan 2.29.1, Clang 15; independent `CONAN_HOME=~/work/psj/ch-xhost`. `conan create ... --build=missing --conf tools.build:jobs=2` completed with `CREATE_EXIT:0`; package reference `xhost/1.0.10#0bfe06ff9eb27929a97f0c834de8fc14:f1594e0d052927f734b7ddc3330c07cff22d5af5#8173e9340ff20aeeb7f2c4159dc9330f`.
- The official release has no registered upstream test suite. The actual `make check -j2` ran and reported `Making check in man` / `Nothing to be done for 'check'`: upstream total 0, skipped 0, failed 0.
- `test_package` ran the installed `bin/xhost` with six real assertions: executable presence/permission, `-help` status and usage text, and no-display status and diagnostic. Result: 6/6 passed.
- No X server was available on the device, so live X server ACL changes are not covered by the consumer test.
- Configure emitted a non-fatal missing `xorg-macros.pc` message; the release ships generated `configure` and `Makefile.in`, and the device build and checks completed successfully without autoreconf.
