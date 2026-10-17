# xfractint

xfractint (XFractint) is the X11 port of the classic Fractint fractal
generator. It renders and zooms a large variety of fractal types
(Mandelbrot/Julia sets, L-systems, IFS, orbits, and more) in an X11 window,
and ships its own help compiler and data files (.frm, .ifs, .l, .map, .par).

## Features

- Interactive generation and deep zooming of hundreds of fractal types.
- Formula (parser), L-system, and IFS engines plus color map cycling.
- Ships fractint.hlp online help and the stock parameter/formula/map data.

## HarmonyOS adaptation

The upstream build is a recursive set of handwritten GNU Makefiles that
hardcode `CC=/usr/bin/gcc` and glibc-era assumptions. The recipe keeps the
Makefiles untouched and overrides everything on the command line:

- `CC` is pointed at the HNP clang.
- `-fcommon` is added (clang's `-fno-common` default breaks the codebase's
  cross-file tentative definitions; the same fix Debian applies).
- The libx11 include/lib closure is passed explicitly via `CFLAGS`/`LIBS`,
  including `-Wl,-rpath-link` so link-time symbol resolution never relies on
  default search paths.
- `SRCDIR` is baked as `<package>/share/xfractint`, and the recipe installs
  `fractint.hlp` plus the stock data files exactly there.

Two minimal portability patches are applied (see `20.4.10/patches/`):

1. `unix/unix.c`: include `<fcntl.h>` for `O_RDONLY`.
2. `common/editpal.c`: provide the legacy `getw()` that musl libc lacks.

The bundled prebuilt `unix/calmanfx.o` (x86 nasm object) is not used; the
nasm path remains disabled upstream-style (`AS=foo`).

Interactive window presentation requires an X11 display, which HarmonyOS PC
devices do not provide; the headless behavior (clean `Could not open display`
error and exit) is what the test_package verifies.

## Dependencies

- Build: clang, make, X11 client headers (libx11 + xorgproto).
- Runtime: libX11 (from the libx11 Conan package) and the system libc/libm.

## References

- Project: <http://www.fractint.org/>
- Source archive: <http://www.fractint.org/ftp/old/linux/xfractint-20.04p10.tar.gz>
