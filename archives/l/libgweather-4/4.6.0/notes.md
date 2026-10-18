# libgweather-4 4.6.0 notes

## Scope

GNOME weather and world-locations library (GWeather): world locations
database access, timezone and local sun/moon computation, METAR
parsing, and MET Norway/OWM/NWS/Iwin weather backends over libsoup3.
Delivers `libgweather-4.so.0`, pkg-config name `gweather4`, headers
under `include/libgweather-4.0/libgweather`, and the
org.gnome.GWeather4 GSettings schema.

## Upstream

- Tag: 4.6.0 (gitlab.gnome.org/GNOME/libgweather)
- Tarball: https://download.gnome.org/sources/libgweather/4.6/libgweather-4.6.0.tar.xz
- SHA256: `7f5d0e8c9685ef2ff46c2f3a57cae48d7bf3540b2d83921f889ef28e6a876788`

## Dependency-first closure (R36)

- `geocode-glib/3.26.4` (libsoup3 flavour, `geocode-glib-2.0`) —
  delivered by its own run (recipe commit 2fe4241873).
- `gweather-locations/2026.2` — the locations database data package
  (Locations.bin GVariant). 4.6.0's meson.build hard-requires
  `dependency('gweather-locations')` and bakes `GWEATHER_LOCATIONS_DB`
  from its pkg-config `locations_db` variable. The GVariant type
  `(ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))` is identical
  between libgweather 4.6.0's `gweather.gv` and gweather-locations
  2026.2's generator — DB format is compatible across the calendar
  versions.
- glib/2.84.0.1.1, json-glib/1.10.6, libsoup3/3.6.5-r3,
  libxml2/2.15.3.1, zlib/1.3.1.1 — all published; the graph is aligned
  with the official geocode-glib/3.26.4 recipe (single GObject copy:
  the r1-era libsoup statically embedded glib, and two GType domains
  in one process crash g_type_register_static).

## OHOS adaptations (geocode-glib 3.26.4 recipe precedent)

- `introspection=false`, `gtk_doc=false`, `enable_vala=false`
  (g-ir-scanner/vapigen cannot run against cross-built libs).
- glib module .pc compat generation + glib tool variables
  (glib_mkenums/glib_compile_schemas/...) patched into glib-2.0.pc, and
  appended to the PkgConfigDeps-regenerated gio-2.0.pc when it lacks
  them (meson.build's gnome.post_install resolves `glib_compile_schemas`
  from gio-2.0.pc at configure time; CI run3 hit the missing-variable
  ERROR against the registry glib/2.84.0.1.1 package) — gnome.mkenums
  and gnome.post_install read them at configure time.
- gweather-locations.pc `locations_db`/`locations_xml`/`locations_dtd`
  variables re-appended by the consumer recipe: Conan's PkgConfigDeps
  regenerates the .pc with only prefix/lib/include, dropping the
  custom variables upstream meson reads.
- SDK llvm bin + glib tools bin prepended to PATH (meson ar detection,
  glib-compile-schemas at install).
- `libgweather-4.so` re-signed with binary-sign-tool after install
  (OHOS loader requires a valid .codesign section).
- registry-delivered glib ELF tools are rejected by the device loader on
  exec (`Operation not permitted`; CI run4 evidence, local-build glib
  tools execute fine) — package() copies glib-compile-schemas into the
  build dir, re-signs the copy with `binary-sign-tool sign -selfSign 1`
  and runs it with an explicit LD_LIBRARY_PATH (same pattern as the .so
  re-sign and the upstream TAP runs).
- `0001-musl-bindtextdomain-decl.patch`: the OHOS SDK sysroot's
  libintl.h does not declare bindtextdomain(), but the OHOS musl libc
  exports the symbol (same dynamic contract geocode-glib relies on);
  libgweather builds with -Werror=implicit-function-declaration, so
  the prototype is declared explicitly under `#if !defined(__GLIBC__)`.

## Upstream tests

- meson registers 4 TAP tests: test_libgweather, duplicates,
  timezones, metar (libgweather/tests/, install:false). The conan
  build host IS the OHOS armv8 device, so the recipe runs all 4
  freshly built test binaries natively right after the meson build,
  with upstream's environment (LIBGWEATHER_LOCATIONS_PATH ->
  Locations.bin, SCHEMASDIR/SCHEMAS_BUILDDIR baked at compile time,
  GSETTINGS_BACKED=memory, GIO_USE_VFS=local,
  LIBGWEATHER_LOCATIONS_NO_NEAREST=1 for duplicates; the tests spawn
  glib-compile-schemas themselves, glib package bin is on PATH).
- tzdata prerequisite: the timezones tests resolve every locations-DB
  timezone id through GLib GTimeZone, which needs individual TZif
  files (TZDIR). The OHOS image ships only the Android-style
  single-file blob /system/etc/zoneinfo/tzdata — no /usr/share/zoneinfo.
  The recipe splits the blob (473 zones, 2025b) into
  build/zoneinfo and restores two tzdb link ids the DB references
  (Antarctica/South_Pole <- McMurdo, Pacific/Johnston <- Honolulu;
  Johnston was merged into Honolulu in tzdb 2025a — without the
  restore the upstream timezones test fails on 'United States Minor
  Outlying Islands does not have an associated timezone', a data/tzdb
  incompatibility reproducible on any host with tzdata >= 2025a). UTC
  is a GLib builtin. The tree is also packaged as share/zoneinfo so
  consumers can set TZDIR.
- Device results: test_libgweather 7/7 ok (1 SKIP: fr_FR locale
  unavailable), duplicates 2/2 ok, timezones 3/3 ok, metar 1/1 ok.
- The consumer test_package additionally exercises the world DB load,
  nearest-city lookup (Eiffel Tower -> Paris), timezone resolution,
  local sun computation with providers disabled, and
  serialize/deserialize round-trip on the OHOS host.

## Verification

- Local `conan create` (ohos-aarch64 profile) before PR; CI
  re-validates on a clean worker once the companion dependency
  packages are published to the registry (R36).
- 2026-09-30 build chain: meson build 158/158 targets OK on device.
