# libdjinterop 0.24.3 adaptation notes

## Build configuration

- Build system: CMake through Conan 2
- Target: HarmonyOS PC (aarch64)
- Library type: static (`BUILD_SHARED_LIBS=OFF`)
- Source: official `0.24.3` GitHub tag archive
- Source SHA-256: `df41fe39bed9d16d27a3649d237b68edd2cdb6fc71a82cae5cd746d4e4ef6578`

## Dependencies

- `zlib/1.3.1`
- `sqlite3/3.49.1`

`CMakeDeps` exposes the dependency package and target names expected by
upstream CMake: `ZLIB` / `ZLIB::ZLIB` and `SQLite3` /
`SQLite::SQLite3`.

## HarmonyOS adaptation

`patches/0001-CMakeLists.txt.patch` applies the established adaptation from
the published `0.24.3-r1` archive:

- removes `-Werror`, which turns harmless platform warnings into failures;
- enables pkg-config generation when `CMAKE_SYSTEM_NAME` is `HarmonyOS`;
- guards Boost-based upstream tests with `BUILD_TESTING`.

The recipe sets `SYSTEM_SQLITE=ON`, `BUILD_TESTING=OFF`, and `BUILD_DOC=OFF`.

## Consumer test

The test package discovers `DjInterop`, links `DjInterop::DjInterop`, creates a
temporary Engine database with schema 2.20.2, and verifies that its initial
track collection is empty and its version name is non-empty.

## Status

Recipe metadata and the source patch were validated locally. The full Conan
cross-build is delegated to the HarmonyOS CI environment because Conan and the
OHOS profile are not installed in this Windows workspace.

<!-- ARCHIVE-CLOSED -->
