# kiconthemes 6.18.0.2 notes

## Scope

kiconthemes/6.18.0.2 is the version-suffixed (R37 / L0j) re-publication of the
6.18-line karchive dependency repair. Upstream source, OHOS adaptations and
patches are unchanged from 6.18.0/6.18.0.1; only the karchive requirement line
that the published 6.18.0 recipe hard-pinned is corrected.

- **Reported problem (dependency-graph audit)**: the published
  `kiconthemes/6.18.0` ref has exactly one recipe revision
  (`f82185f3a6daed7a2bae8d5f14a6e773`) and it pins the static
  `karchive/6.19.0`. Every other 6.18-line consumer (`knewstuff/6.18.0`,
  `libkdegames/26.04.0`, `kxmlgui/6.18.0`, `akonadi/25.12.3`, ...) pins
  `karchive/6.18.0`, so the graph is dragged out of the 6.18 line and conan
  aborts with:

  ```
  ERROR: Version conflict: Conflict between karchive/6.18.0 and karchive/6.19.0 in the graph.
  ```

- **Repair**: require the shared `karchive/6.18.0` published for the same
  generation line, so the 6.18 closure stays single-version and consumers no
  longer need a `karchive/6.18.0, override=True` rescue.
- **Why a new version instead of a 6.18.0 revision**: the registry rejects a
  second recipe revision under an already-published version (HTTP 409), so the
  bad `6.18.0` ref cannot be replaced in place; a new version suffix is the
  governed non-destructive publication path (same pattern as
  `kpackage/6.18.0.2`). The old `6.18.0` artifact is left untouched.

## API verification — kiconthemes uses no karchive-6.19-only API

The task explicitly requires verifying that the 6.19 karchive API surface is
not actually used before lowering the requirement. Evidence (source
`kiconthemes-6.18.0.tar.xz`, SHA-256
`b971460949fafc98e7ae293f35635c2fd6101a6fc46b2f4fce64bb21440ece04`):

1. **Only one KArchive code path exists** — `KCompressionDevice`:
   - `src/CMakeLists.txt:66`: `KF6::Archive       # for KCompressionDevice`
   - `src/kiconloader.cpp:34`: `#include <KCompressionDevice>`
   - `src/kiconloader.cpp:669`:
     `device.reset(new KCompressionDevice(path, KCompressionDevice::GZip));`

   No other KArchive/KZip/KTar/KAr API is referenced anywhere in the tree
   (`grep -rn "KF6Archive|KArchive|KTar|KZip|KCompressionDevice"` yields the
   hits above plus the two CMake version checks).
2. **Upstream floor is 6.18.0, not 6.19.0**:
   - `CMakeLists.txt:4`: `set(KF_DEP_VERSION "6.18.0")`
   - `CMakeLists.txt:69`: `find_package(KF6Archive ${KF_DEP_VERSION} REQUIRED)`
   - `KF6IconThemesConfig.cmake.in:14`:
     `find_dependency(KF6Archive "@KF_DEP_VERSION@")`
3. **The header is byte-identical across the two karchive builds**:
   `diff -u karchive-6.18.0/src/kcompressiondevice.h
   karchive-6.19.0/src/kcompressiondevice.h` → empty (no additions,
   deprecations or removals), so the `KCompressionDevice(QString,
   CompressionType)` constructor and the `GZip` enum value used are present in
   `karchive/6.18.0`.
4. **Independent build evidence**: kiconthemes/6.18.0.1 ships the same source,
   patch set and closure (`karchive/6.18.0`) and already passed the upstream
   suite and `test_package` (see `manifest.yaml` `test_results` and
   `reports/test-report.md`).

## Adaptations (unchanged from 6.18.0/6.18.0.1)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KICONTHEMES_USE_QTQUICK=OFF` avoids Qt6Qml/Qt6Quick.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `USE_BreezeIcons=OFF` avoids the unpublished KF6BreezeIcons package.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `include(ECMQmlModule)` is patched out for the Qt6Qml-free baseline, and the
  optional QtQuick autotest is guarded behind `KICONTHEMES_USE_QTQUICK`.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time. The 6.26.0 recipe additionally prepends `/system/lib64` to
  `LD_LIBRARY_PATH` for it; the 6.18-line recipe does **not** set that entry,
  and the measured 6.18.0.2 run configured and executed `qtpaths` successfully
  without it.
- `OPENSSL_*` cache variables and a minimal `PkgConfig::LibZstd` imported
  target are supplied consumer-side so the `KF6ArchiveConfig.cmake` /
  `KF6ArchiveTargets` `find_dependency()`/`LINK_ONLY` chains resolve.
- `package_info()` now declares `bindirs = ["bin"]` because the package ships
  the `kiconfinder6` CLI tool; the software-level `commands.json` registers
  `6.18.0.2` accordingly (R38 / PF8 / CI L0k convention, same as `kpackage`).

## Dependency-line check (measured)

```
$ conan graph info --requires=kiconthemes/6.18.0 --requires=knewstuff/6.18.0 ...   # published ref
ERROR: Version conflict: Conflict between karchive/6.18.0 and karchive/6.19.0 in the graph.

$ conan graph info --requires=kiconthemes/6.18.0.2 --requires=knewstuff/6.18.0 ... # this ref
exit=0, karchive/6.18.0 only (no karchive/6.19.0 node)
```

## Verification

See `manifest.yaml` (`test_results`) and `reports/test-report.md` for the
measured build/test run, and `reports/audit-result.json` for the W4 audit.
