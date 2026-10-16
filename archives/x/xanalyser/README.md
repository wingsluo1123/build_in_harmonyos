# xanalyser

XAnalyser is a real-time audio frequency spectrum analyser for the X Window
System, written by Arvin Schnell (1998-2008). It reads PCM samples from the
sound card or from a file, runs a fast Fourier transformation over them and
draws the resulting spectrum (plus a scope view of the waveform) in a window.
The complete user interface is built directly on the X Toolkit (Xt) and the
Motif widget set (`libXm`); the window icons are XPM images compiled into the
binary.

## Functionality

- Live spectrum display (FFT) with configurable sample rate, sample length and
  resolution; configurable upper/lower dB limits, alpha (averaging) and decay.
- Two display widgets: spectrum (`Analyser`) and time-domain scope (`Scope`).
- Input sources: sound card (`pcm-oss`, `pcm-alsa`) and disk files
  (`pcm-wav`, `pcm-cdr`), selectable with `-soundcard` / `-diskfile`.
- Command line: `-rate`, `-length`, `-resolution`, `-device`, `-dcadjust`,
  `-stereo`, `-file`.
- Motif app-defaults resource file (`XAnalyser.ad`) with compiled-in fallbacks.

## OHOS adaptation

- `motif/2.3.8` supplies `libXm.so.4` together with `Xm/*.h`; Motif does not
  exist upstream of this repository and is a locally adapted package. The
  recipe requires it (plus `libxmu` / `libxpm` directly, since the upstream
  link line uses `-lXmu -lXpm` and motif does not pull them in).
- Two X11 tracks exist in the artifact repo (`libx11/1.8.13` + `libxext/6.4.0.1`
  for the Motif family, `libx11/6.4.0` for the cmd-pkgs family). The recipe
  follows the merged `xmhtml/1.1.10` resolution: force `libx11/1.8.13`. The
  `libxpm` binary for that track is not published, so CI's `--build=missing`
  compiles `libxpm/3.5.17` from source.
- The build is performed **in-source** and with `make -j1` (the OHOS sandbox has
  no `mkfifo` for make's jobserver); `configure`'s `umask 077` is rewritten to
  `022` (E011, HMDFS) and the autotools helpers get their executable bit back.
- The source-root `VERSION` file is moved out of the include root after
  `configure` (HMDFS is case-insensitive and the C++17 `#include <version>`
  would otherwise pick it up) - no source patches are needed at all.
- `-Wno-c++11-narrowing` for the 2008-era C++ braced initialisers under
  `cppstd=17`.
- `install-data-hook` writes the app-defaults file to the absolute
  `/usr/share/X11/app-defaults`; the recipe relocates it to
  `<package>/share/X11/app-defaults`.

## OS limitation (headless)

Neither this build machine nor HarmonyOS provides an X server or Wayland, so
any code path that reaches `XtAppInitialize`/`XtOpenDisplay` cannot succeed:
the program prints upstream's `Error: Can't open display: ` and exits with
status 1. The GUI itself (Motif widgets, spectrum drawing, sound-card capture)
is therefore not exercisable on the platform; this is declared in
`1.32/test_package/MANIFEST.yml`. The consumer test verifies instead that the
binary is a native OHOS/musl AArch64 ELF whose complete Motif/X11 dependency
closure is resolvable and loadable at runtime.

## Dependencies

- `motif/2.3.8` — Motif widget set (`libXm.so.4`) + `Xm/*.h` (build & run).
- `libxmu/1.3.1.1`, `libxpm/3.5.17` — linked directly by the upstream
  `LDADD` (`-lXmu -lXpm`).
- `libx11/1.8.13`, `libxt/1.3.1`, `libxext/6.4.0.1`, `libsm/1.2.6`,
  `libice/1.1.2`, `xorgproto/2025.1` — X11 client libraries and protocol
  headers (also pulled in by `motif`/`libxt`).

## References

- http://arvin.schnell-web.net/xanalyser/ (official project page and downloads)
- `doc/xanalyser.1` in the source tarball (man page)

## Versions

| Version | Status |
| --- | --- |
| 1.32 | built |
