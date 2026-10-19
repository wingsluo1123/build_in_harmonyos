# KDb

KDb is KDE's database connectivity library (the database layer shared with
Kexi, released from the standalone kdb repository). It provides driver plugin
management (`KDbDriverManager` / `KDbDriverMetaData`), connection and
transaction handling (`KDbConnection`), table/field schema modeling
(`KDbTableSchema` / `KDbField`), queries and expressions, and a SQL parser
with a pre-generated flex lexer. The library links Qt5 Core/Gui/Widgets and
KF5::CoreAddons publicly, and Qt5::Xml + ICU::i18n privately. The sqlite3
driver (a Qt plugin `kdb_sqlite3.so` plus its ICU extension) and the
`kdb3_sqlite3_dump` CLI are built and installed alongside.

## OHOS adaptation

- `CMAKE_SYSTEM_NAME=Linux` is forced: the OHOS Conan toolchain maps
  `os=OHOS` to `CMAKE_SYSTEM_NAME=HarmonyOS`, for which CMake defines
  neither `UNIX` nor a platform module, and the build is flagged as
  cross-compiling. `KDECMakeSettings` applies its POSIX RPATH settings only
  under `if(UNIX)` and ECM registers the upstream ctest cases only when not
  cross-compiling; the Linux platform (same libc / clang driver on OHOS PC)
  restores `UNIX=1` and a native build.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` is required by this source: the root
  `CMakeLists.txt` includes `KDEFrameworkCompilerSettings`, whose
  `KDEMetaInfoPlatformCheck` module `file(STRINGS metainfo.yaml ...)` at
  include time, and the kdb-3.2.0 release tarball ships no `metainfo.yaml`.
- `KDE_INSTALL_USE_QT_SYS_PATHS=OFF` installs plugins to
  `<prefix>/lib/plugins/kdb3`; consumers load the sqlite3 driver through the
  Qt library-path mechanism (`QT_PLUGIN_PATH`), which is how the upstream
  tests and the test_package bring the driver in.
- The HeadersTest nested consumer project resolves its
  `find_package(ECM/Qt5/KF5/KDb)` calls through a `CMAKE_PREFIX_PATH`
  environment variable composed by the recipe; the entries are joined with
  `os.pathsep` because CMake splits this variable on the platform path
  separator (a `;`-joined multi-entry value is taken as one invalid prefix
  and fails every find_package).
- The `icu` package is static, and the `FindICU` module bundled in this tree
  creates bare imported libraries without inter-component edges, so a patch
  requests the `data` component and appends the `i18n -> uc -> data` link
  chain (needed under `-Wl,--no-undefined`).
- The pre-generated flex scanner still uses the `register` storage class,
  which `cppstd=17` diagnoses as the `-Wregister` error; a patch adds
  `-Wno-register` to the scanner's compile flags.
- `PYTHON_EXECUTABLE` is pinned to the interpreter running Conan:
  `KDbCreateSharedDataClasses` runs `tools/sdc.py` at configure time via
  `find_package(PythonInterp 2.6)`.
- `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` (E537) plus re-signing every packaged
  ELF with `binary-sign-tool`, and an unversioned `DT_SONAME`
  (`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`), per the family precedents.

## Dependencies

- Build: ecm (extra-cmake-modules)
- Runtime/compile: qt5-qtbase (Core/Gui/Widgets/Xml), kcoreaddons5
  (KF5::CoreAddons), icu (static, i18n/uc/data), sqlite3 (driver + CLI)

## References

- Homepage: https://invent.kde.org/office/kdb
- Sources: https://download.kde.org/Attic/kdb/src/kdb-3.2.0.tar.xz
