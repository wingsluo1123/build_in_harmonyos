# kcolorscheme 6.18.0.3 notes

## 6.18.0.3 revision (2026-10-14)

**修订原因**：`6.18.0.2` 的**已发布二进制里烤死了绝对路径** —— 真机
`llvm-readelf -d libKF6ColorScheme.so` 实测 4 条：

```
NEEDED [/…/p/kconfe211c1d086c2f/p/lib/libKF6ConfigGui.so]
NEEDED [/…/p/b/kguia5c3aa78c951c4/p/lib/libKF6GuiAddons.so]   ← kguiaddons 构建目录，复用时不存在
NEEDED [/…/p/ki18n7848f8ccdc091/p/lib/libKF6I18n.so]
NEEDED [/…/p/kconfe211c1d086c2f/p/lib/libKF6ConfigCore.so]
```

只要下游**复用**这份制品，加载就必然失败：`kconfigwidgets/6.18.0` 自己的 `build()` 测试因此
`0% tests passed, 7 failed out of 7`，并连带 `kxmlgui` / `kiconthemes`（#14337 整条链红）。
根因是依赖 `kguiaddons/6.18.0` **缺 SONAME**（见 `kguiaddons/6.18.0.1` 的修订说明）。

**本修订**：

- 依赖改为 `kguiaddons/6.18.0.1`（`override=True`）——该版本已带 SONAME，链接结果只记
  `libKF6GuiAddons.so.6`；
- `generate()` 显式注入 `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG = "-Wl,-soname,"`，
  使本包今后产出的库不再把路径烤进 `DT_NEEDED`（与 `kio` 配方同法）；
- `package()` 增加包内 ELF 自签名（`llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1` + `chmod 755`）；
- `_run_upstream_tests()` 前调用 `_repair_absolute_needed_entries()`，对依赖链残留的绝对
  `DT_NEEDED` 做软链补齐 / 重签兜底。

## Scope

This package is part of the Akonadi KF 6.18 baseline. It is based on the
existing remote 6.14.0 recipe and adds a mainline-ready 6.18.0 package
directory without modifying the 6.14.0 branch.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation in the
  cross-build package path.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies are aligned to the KF 6.18 baseline:
  `kconfig/6.18.0`, `kguiaddons/6.18.0`, and `ki18n/6.18.0`.
- Upstream requires `Qt6GuiPrivate` when Qt6Gui is 6.10 or newer; this is
  expected to come from `qtbase/6.11.1`.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `14e99e74cc636640ac8d705f2878d72d0379fff671e75c0f138302489898d651`.
- No source patch is required for the 6.18.0 minimal OHOS baseline.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kcolorscheme-r2.log`.
- Full package reference: `kcolorscheme/6.18.0#43b1e2bcfcefc51b5619858b6316f5ff:742b53369c1b9ae12f3c09d348f766caa772598a#c5789ec1c12eb74c7fa7295590b1fc20`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 1/1: `kcolorschemetest`.
- Conan `test_package` passed 1/1 with a `KColorScheme` consumer smoke that
  constructs the scheme and verifies a valid background brush.

## 6.18.0.2 revision (2026-10-01)

Provider migration plus the Qt6GuiPrivate/XKB dependency fix. Upstream sources, build logic
and test assertions are unchanged; `conandata.yml` has no patches, so no patch key change is
required.

- `qtbase/6.11.1` -> `qtbase/6.11.1.3, override=True` (`kguiaddons/6.18.0` still declares the
  old provider, so the root requirement overrides it).
- `kconfig/6.18.0` -> `6.18.0.1`, `ki18n/6.18.0` -> `6.18.0.2` (both already published with the
  unified provider).
- **New direct dependency `libxkbcommon/1.6.0`.** `qtbase/6.11.1.3` installs
  `lib/cmake/Qt6/Qt6GuiPrivateConanDependencies.cmake` (loaded by qtbase patch 0014) and
  `lib/cmake/Qt6/conan/FindXKB.cmake`, whose first step is
  `find_package(libxkbcommon CONFIG QUIET)`. Without a Conan config for `libxkbcommon` it falls
  back to Qt's system finder and the configure step fails with
  `Qt6GuiPrivate could not be found because dependency XKB could not be found`. Declaring the
  dependency makes CMakeDeps emit the config; `generate()` additionally sets
  `XKB_INCLUDE_DIR`/`XKB_LIBRARY` so the fallback path also works.
