# kwidgetsaddons 6.28.0 notes

## Scope

This package is part of the KF6 6.28 train (task: kwidgetsaddons, 【依赖项】).
It updates the existing HarmonyOS PC recipe from 6.26.0.1 to KDE Frameworks
6.28.0. Dependencies: ecm/6.28.0 (build) + qtbase/6.11.1 (required).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_PYTHON_BINDINGS=OFF` is still required for 6.28.0: the upstream
  CMakeLists keeps the option defaulting to ON (auto-off only for
  ANDROID/APPLE/WIN32/HAIKU or static builds), and Python bindings would
  otherwise try to discover Shiboken6/PySide6.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery
  (not published to ohpcd).
- `BUILD_TESTING=ON` runs the upstream CTest autotests during the Conan
  build.
- The OHOS headless runner excludes `ktooltipwidgettest` and
  `kwidgetsaddons-kcolumnresizertest` (6.18.0 precedent; the only two in
  6.28.0 as well).
- `ecm_install_po_files_as_qm(poqm)` is disabled by patch 0001 because
  Qt6LinguistTools is not part of the qtbase package published to ohpcd.
- `DT_SONAME` link-flag injection (`-Wl,-soname,`) is kept from the 6.26
  recipes: OHOS CMake has no `Platform/HarmonyOS` module, so without the
  flags lld emits no `DT_SONAME` and consumers record an absolute build path
  in `DT_NEEDED`.
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` (set as both toolchain variables
  and cache variables) is added for the device: the HMDFS user volume
  rejects `symlink()` with EPERM, so the versioned `libKF6WidgetsAddons.so.6`
  chain CMake creates after linking fails the build (`CMake Error: failed to
  create symbolic link ... Permission denied`). Libraries are emitted under
  the plain `libKF6WidgetsAddons.so` name while the explicit `-soname` flag
  still bakes a real `DT_SONAME`, so consumers keep recording a relocatable
  `NEEDED` name (DRAFT-cmake-harmonyos-system-name-soname; kcolorpicker /
  expat precedent).
- ECM 6.28 KDEInstallDirs6 runs the qtbase `qtpaths` host tool during
  configure (ecm_query_qt -> QT_INSTALL_PREFIX); the sandbox LD_LIBRARY_PATH
  contains an incompatible libc++_shared.so which shadows the compatible
  one, so `/system/lib64` and the qtbase lib dir are prepended
  (kconfig 6.26.0 / bluez-qt 6.28.0 / kitemviews 6.26.0 precedent).

## Upstream changes 6.26.0 -> 6.28.0

- `CMakeLists.txt` delta is exactly two lines: `KF_VERSION` 6.26.0 ->
  6.28.0 and `find_package(ECM 6.26.0)` -> `(ECM 6.28.0)`. The ECM minimum
  is the only new dependency requirement; ohpcd publishes ecm/6.28.0
  (built 2026-10-14), so the recipe moves its build dependency to
  ecm/6.28.0 directly instead of lowering the requirement via patch
  (cf. kquickcharts 6.28.0, which patched down to ecm/6.26.0 while
  ecm 6.28 was absent from the registry).
- `src/CMakeLists.txt`: `kmimetypeeditor.cpp/.h` move behind `if(NOT IOS)`
  (still built on OHOS), `DEPRECATION_VERSIONS` gains `6.0`,
  `ecm_qt_declare_logging_category` drops `DEFAULT_SEVERITY Warning`
  (ECM 6.28's default). No functional change for OHOS.
- Deprecated-API headers (kjobwidgets.h, knewpassworddialog.h,
  knewpasswordwidget.h, kpassworddialog.h, kpasswordlineedit.h) reorder the
  export macro onto its own line; no ABI change.
- `autotests/CMakeLists.txt` is byte-identical to 6.26.0 (26 CTest
  entries); changes under autotests/ are test-source touch-ups only.
- Source diff otherwise limited to poqm translations (`.po` files) and
  `src/kcharselect-data`; the OHOS adaptation surface is unchanged.

## Verification

Local prechecks:

- Source SHA256 verified against the official KDE `.sha256` file:
  `6bb6a22e40bc8cfaeda08276b771488294ad417e7802b27bdc455202afdabd7d`.
- Patch 0001 verified with patch_ng (the engine conan uses), strip=0,
  against the unpacked 6.28.0 source: parses (1 file / 1 hunk) and applies
  cleanly with zero context refresh.

OHOS `conan create` verification (device, 2026-10-16): PASS — gates
G0/G1/G2/G3/G4 all pass; upstream CTest 24/24 executed autotests passed
(0 failed; two OHOS-headless exclusions), test_package 1/1 passed
(KPageWidgetModel consumer). Full reference:
`kwidgetsaddons/6.28.0@ohpcd/stable#e6c46cfaee1b80d95e5b65f255048e14`
(package `57ffd8c720a5bfee7e8827990cd6550a49181c1b`).

## Submit 流程记录

- 2026-10-16 设备配方验证 PASS（G0-G4 / L2-L5；CTest 24/24；test_package
  1/1）；设备首轮死于 HMDFS symlink EPERM（`.so.6` 版本化软链），
  以 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` 修复后全绿。
- MR 已开：OpenHarmonyPCDeveloper/build_in_harmonyos#16128（分支
  `feat/kwidgetsaddons-6.28.0`）。
- 离线 AI 检视（真机 AtomCode，R1）：P0/P1/P2 = 0。P3×3 处置——
  ① `test_package/test.cpp:1` 注释版本串残留 6.26.0（本 PR 引入）→
  已整改为 6.28.0；② `conanfile.py` 硬编码 `BUILD_SHARED_LIBS="ON"`
  = 全库 706 配方既存惯例、非本 PR 引入 → 记录不修；③ SONAME 变量
  未加 `settings.os` 守卫 = kcolorpicker 先例同款 → 不采纳。另整改
  `manifest.yaml` `full_reference` 补包 ID 后缀（与同包前版一致）。
- 平台代码审查首轮 [阻塞]×1：`reports/conan-create.log` 属规则禁止提交的
  构建日志（含设备绝对路径/制品仓信息）→ 已从 PR 移除；脱敏的
  `reports/conan-verify-report.md` 保留随档。
- CI / 提审记录：见 MR #16128 评论区。
