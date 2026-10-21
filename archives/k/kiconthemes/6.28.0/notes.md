# kiconthemes 6.28.0 notes

## Scope

This package is part of the KF6 6.28 line (dependency activity). It carries
the existing HarmonyOS PC adaptation forward from 6.26.0 (archive in this
repository) to KDE Frameworks 6.28.0, following the same pattern as the other
6.28.0 chain packages (kservice 6.28.0 and karchive 6.28.0 precedents).

## Upstream verification

- Upstream tag `v6.28.0` verified via
  `git ls-remote https://invent.kde.org/frameworks/kiconthemes.git`:
  `refs/tags/v6.28.0` -> annotated tag object
  `abd24a0c88f912123bbadb7670200591c988f0d1`, peeled commit
  `34d5044190d61df9d26e32a0b5b895ade4d87046`.
- Tarball fetched from the NJU KDE mirror (the CI workers cannot reach
  download.kde.org; same as karchive 6.28.0) and its SHA-256
  `edf83069f25f8edf759d07502a6f8302c8c064cd562651deedefe6393fefcace`
  cross-checked against the official
  `download.kde.org/stable/frameworks/6.28/kiconthemes-6.28.0.tar.xz.sha256`.

## Upstream changes (6.26.0 -> 6.28.0)

- Root `CMakeLists.txt`: `KF_VERSION`/`KF_DEP_VERSION` become 6.28.0,
  `find_package(ECM 6.28.0)`, and the disabled-deprecation KF baseline
  moves from 6.23 to 6.27.
- `autotests/`: new `kiconbutton_unittest` (KIconButton property defaults
  and reset/size behavior); all pre-existing autotest sources are byte
  identical.
- `src/widgets/kicondialog.cpp`: item activation and the OK button now
  share one accept-selected handler.
- `src/tools/ksvg2icns/ksvg2icns.cpp`: the `iconutil` invocation is
  compiled out on `Q_OS_IOS`.
- `po/` translation catalogs updated; no other source changes.

## Upstream dependency check (6.28.0)

- `find_package(ECM 6.28.0 NO_MODULE)` - satisfied by the published
  `ecm/6.28.0` tool package.
- `REQUIRED_QT_VERSION 6.9.0` - satisfied by `qtbase/6.11.1`.
- `KF_DEP_VERSION "6.28.0"` drives `find_package(KF6Archive/KF6I18n/
  KF6WidgetsAddons/KF6ColorScheme 6.28.0 CONFIG REQUIRED)`. The published
  KF6 stack stops at 6.26.0 (with the .1 fix releases for kwidgetsaddons),
  so patch 0001 lowers `KF_DEP_VERSION` to `6.26.0` (kservice 6.28.0
  precedent); the ECM 6.28.0 floor is left untouched.
- `KICONTHEMES_USE_QTQUICK` defaults to ON; Qt6Qml/Quick are not published
  to ohpcd, so the option stays OFF and the unconditional
  `include(ECMQmlModule)` is patched out, with `kquickiconprovidertest`
  guarded behind the option.

## Adaptations (delta against the 6.26.0 recipe)

- `KF_DEP_VERSION` lowered to the published 6.26.0 baseline by patch
  `0001-ohos-adaptations.patch`; ECM `tool_requires` raised to 6.28.0.
- The new upstream `kiconbutton_unittest` runs in the CTest sweep (6/6).
- test_package stages the dependency runtimes next to the test binary with
  `os.link()` and falls back to `shutil.copy2()` when the filesystem denies
  a link (the OHOS user volume rejects `symlink(2)` with EACCES); CI keeps
  the original staging behavior.
- Unchanged from 6.26.0: `KF_IGNORE_PLATFORM_CHECK=TRUE`,
  `USE_DBUS=OFF`, `USE_BreezeIcons=OFF`, `BUILD_DESIGNERPLUGIN=OFF`,
  `KF_SKIP_PO_PROCESSING=ON`, the ECM module path wiring,
  `/system/lib64` prepended to `LD_LIBRARY_PATH`, headless
  `QT_QPA_PLATFORM=offscreen` autotests, absolute DT_NEEDED normalization,
  `.codesign` removal plus `binary-sign-tool selfSign`, and
  `cmake_find_mode=none` in package_info.

## Verification (OHOS aarch64 real device, profile ohos-aarch64-full)

- `conan create` exit code 0; package
  `kiconthemes/6.28.0@ohpcd/stable#a4b14716bed8b5c003f3c3fd36632bf6:8935f3f60d62a98ae9eec680abcd71b2d6234b24#70f1920d2f63bc5696567dd5e9a517b3`.
- Upstream CTest 6/6: kiconloader_resourcethemetest, kicontheme_unittest,
  kiconengine_scaled_unittest, kiconbutton_unittest, kicondialog_unittest,
  kpixmapsequenceloadertest.
- `kiconloader_unittest` subset 29/29 (one shared-mime-info data row is
  unavailable in the current OHOS baseline), `kiconengine_unittest` subset
  8/8 (`testMode` needs BreezeIcons, which is disabled).
- Consumer end-to-end 9/9: an isolated XDG home with a generated icon theme
  exercises `KIconLoader::global()`/`loadIcon`, `KIconTheme`
  construction/enumeration and `KIconEngine::pixmap`; the test_package CTest
  entry also passes 1/1.
- `ohc-run.py conan-verify kiconthemes 6.28.0 --profile ohos-aarch64-full`:
  Verdict PASS across G0/G1/G2/G3/G4/L2/L4/L5. L2/L4/L5 are non-blocking
  skips because the cache-path lookup did not resolve the package id under
  conan 2.29.1 (same behavior as kservice 6.28.0).

## Notes

- The OHOS user volume (HMDFS) rejects `symlink(2)`; staging falls back to
  hardlinks/copies as described above.
- `make` prints `jobserver mkfifo ... Operation not permitted` on the device;
  the build completes normally with the requested parallelism.
