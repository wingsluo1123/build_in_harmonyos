# klickety 26.04.0 notes

## Scope

KDE SameGame/Clickomania adaptation (color-matching puzzle game): a Qt6/KF6
QGraphics application built on the KDEGames6 library (libkdegames 26.04.0,
published on the ohpcd registry).

## Upstream shape (26.04.0 tarball)

- Qt6 6.5+/KF6 6.0+ CMake project (ECM toolchain), Qt6 Widgets.
- Single executable: `klickety` (QApplication GUI).
- Upstream REQUIRED KF6 set: CoreAddons, Config, Crash, WidgetsAddons,
  I18n, ConfigWidgets, XmlGui, KIO, DBusAddons, IconThemes + KDEGames6 6.0.0.
- DocTools listed as OPTIONAL_COMPONENTS only (handbook generation).
- No test suite: no tests/, autotests/ or add_test() anywhere (N=0).

## Adaptations

- patches/0001-ohos-skip-kdoctools.patch: DocTools removed from
  OPTIONAL_COMPONENTS; add_subdirectory(doc) and kdoctools_install(po)
  dropped. kdoctools is not part of the published KF6 6.18/6.26 closure;
  the DocBook handbook is not a runtime requirement (kfourinline 26.04.0
  precedent).
- KF_IGNORE_PLATFORM_CHECK=TRUE, KF_SKIP_PO_PROCESSING=ON (standard KDE
  OHOS set, libkdegames/kfourinline precedent).
- karchive/6.18.0 pinned with override=True (libkdegames 26.04.0 graph
  precedent: newest kiconthemes/6.18.0 revision requires karchive/6.19.0,
  knewstuff/6.18.0 requires karchive/6.18.0).
- Qt6Svg resolved from qtsvg/6.11.1 via QT_ADDITIONAL_PACKAGES_PREFIX_PATH
  (libkdegames verified pattern).
- ECM_MODULE_PATH set manually + conan_cmakedeps_paths.cmake written
  manually (cmake_find_mode=none packages are not added to CMAKE_PREFIX_PATH
  by CMakeDeps).
- -Wl,-z,max-page-size=0x1000 linker pin (OHOS musl loader rejects the
  default lld 0x10000 multi-RW-LOAD layout; kfourinline 26.04.0 precedent).
- Host tools (moc/uic/rcc, kconfig_compiler) are OHOS binaries from the
  conan packages: build env prepends /system/lib64 + SDK llvm/lib +
  dependency lib dirs to LD_LIBRARY_PATH (audiocd/kconfig precedent).

## Verification

OHOS `conan create` (local, aarch64, clang, Release) - PASSED:

- All dependency packages installed (ohpcd registry).
- Upstream test suite: N=0 (upstream registers none).
- test_package smoke: 2/2 assertions passed:
  - klickety --version prints "klickety 2.1.26040" and exits 0
    (QT_QPA_PLATFORM=offscreen).
- W3 local CI passed (L0 pass, L1 negative test confirmed, L5 pass).

---

### 对话 #1 — 移植适配

- KIO removed (kio/6.14.0 与 KF6 6.18 闭包冲突)
- libkdegames/26.04.0.1 避免 kconfig 版本冲突
- Patches: 0001 (移除 KIO/DocTools), 0002 (移除 KF6::KIOWidgets + 添加 KF6::CoreAddons), 0003 (KUrlRequester→QLineEdit)

### 对话 #2 — 运行时修复

- kiconthemes registry 缓存有相对 DT_NEEDED (`../../bin/libKF6IconThemes.so`)
- 需手动在 registry cache 创建 bin/ 文件夹兼容层
- test.sh 版本匹配：KDE 编码 `26.04.0` → `2.1.26040`
---

**编译结束**: 2026-10-15 17:22
**最终状态**: published
