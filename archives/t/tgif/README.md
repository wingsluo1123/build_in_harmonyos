# tgif

tgif is an interactive 2-D drawing tool for X11. It edits `.obj` vector drawings
with objects, text, splines and raster images, plus optional HyperGraphics
(`tgwb`) and Tangram-II extensions, and exports PostScript/EPS via its built-in
`-print` filter mode.

## Features

- Interactive object-based drawing (arcs, boxes, polygons, splines, text).
- `.obj` document format with pages, attribute groups and symbol libraries.
- PostScript / EPS export through the `-print` filter (no display required).
- Optional PNG/JPEG/GIF import-transcode helpers.
- HyperGraphics (`tgwb`) and Tangram-II side features.

## HarmonyOS adaptation

The upstream release tarball is packed from an already-configured source tree,
so it ships `config.status`, `config.h`, `config.log` and `Makefile` with the
maintainer's hardcoded `srcdir`. The recipe drops those residues for the Conan
out-of-tree (VPATH) build. The Makefile's compile-time `-D` definitions are
moved from `CFLAGS` to `AM_CPPFLAGS` so the Conan toolchain `CFLAGS` are no
longer shadowed, the vestigial `-lXext/-lSM/-lICE/-lXmu` link entries (which
have no referenced symbol) are pruned, and `configure`'s `umask 077`
`config.status` temp directory is relaxed to a normally-writable directory
(HMDFS forces setgid; a `umask 077` directory is not writable even by its
owner).

## Dependencies

- libx11/1.8.13
- libxt/1.3.1
- zlib/1.3.2

## Runtime notes

The device has no X server, so the interactive drawing UI cannot be exercised
here; the packaged binary is verified through its display-less `-print
-justversion` path and its deterministic "Can't open display" startup failure.
`bin/tgif` is dynamically linked to the Conan X11 stack and carries no RPATH, so
it needs the `conanrun` environment (`LD_LIBRARY_PATH`) at runtime. tgif's
default temporary directory is compiled in as `/tmp/`, which is read-only on
HarmonyOS; at runtime it can be redirected with the `Tgif.TmpDir` X resource (or
`Tgif.TmpDirInHomeDir: true`).

## References

- https://sourceforge.net/projects/tgif/
