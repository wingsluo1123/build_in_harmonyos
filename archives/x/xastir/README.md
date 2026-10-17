# xastir

xastir (X Amateur Station Tracking and Information Reporting) is the classic
open-source APRS client by the Xastir Group: a map-centric station tracking
and information tool for amateur radio. The entire user interface is built
on the X Toolkit (Xt) and the Motif widget set (`libXm`).

## Functionality

- Renders APRS stations/objects/items on scrolling maps from GeoTIFF,
  TIGER/Line, shapefile (shapelib) and online map sources via libcurl.
- Interfaces with TNCs (KISS/AX.25, via libax25), AGWPE, GPS receivers and
  internet APRS-IS feeds; can run an x-spider TCP/UDP server.
- Berkeley DB map caching, pcre2-compiled station name/attribute filters,
  DBFAWK-driven FCC/U.S. Census database lookups, weather/alert display
  (NWS), SAR/map annotation tools.
- `callpass` helper: computes the APRS-IS login passcode for a callsign
  (source is pure C and never opens a display, so it stays executable on a
  headless target; under the upstream link rule it is still linked with the
  project's full LIBS closure).

## OHOS adaptation

- First adapted version: 2.2.4 (see [2.2.4/notes.md](2.2.4/notes.md) for the
  full engineering log).
- Bootstrap required: the official release tarball ships no configure
  (aclocal + autoheader + autoconf + automake -a -c, with `mkdir m4` first).
- Four portability patches for the OHOS musl libc, all using capability
  probes rather than platform-identity macros: an AC_CHECK_FUNCS probe for
  the optional POSIX thread-cancellation entry points (with the call sites
  guarded, never faked), rindex→strrchr, and the glibc setproctitle
  emulation guarded by defined(__GLIBC__).
- ImageMagick/GraphicsMagick import disabled (upstream caps
  MagickLibVersion at 0x0700; the registry only offers 7.1.2.29 = 0x712);
  raster/vector map import remains covered by the GeoTIFF + shapelib path.
- GUI cannot be exercised without an X server; the packaged `callpass`
  provides the executed-behavior evidence and `xastir` is asserted
  headless (see 2.2.4/test_package).
