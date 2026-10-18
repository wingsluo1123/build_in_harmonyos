# killbots

KDE Gear 经典游戏 killbots（BSD robots 的 Qt/KDE 移植）适配——QGraphics 回合制
策略游戏：玩家机器人躲避并诱导机器人互相撞击（Qt6/KF6 + KDEGames6）。

## OHOS adaptation

- Builds the KDE release tarball (26.04.0) with CMake on HarmonyOS PC (aarch64).
- `build()` 内直接替换 `CMakeLists.txt`，移除 KF6 DocTools、`doc/` 子目录与
  `kdoctools_install(po)`（kdoctools 未在已发布 KF6 6.18/6.26 闭包中，handbook
  非运行时必需；klickety 26.04.0 同款处置）。
- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台检测（OHOS 不在 KDE 平台列表）。
- `KF_SKIP_PO_PROCESSING=ON` 跳过翻译目录生成。
- `ECM_MODULE_PATH` 手动设置 + 手写 `conan_cmakedeps_paths.cmake`
  （qtbase/KF6 使用 `cmake_find_mode=none`）。
- `-Wl,-z,max-page-size=0x1000`（OHOS musl 加载器 workaround）。
- 宿主工具（moc/uic/rcc/kconfig_compiler）为 OHOS 二进制：构建环境前置
  `/system/lib64` + SDK llvm/lib + 依赖 lib 目录。
- `src/CMakeLists.txt` 额外需要 `Qt6::Xml`（klickety 不需要）。

## Dependencies

- `qtbase/6.11.1` + `qtsvg/6.11.1`: Qt6 基础
- `karchive/6.18.0` (override): KF6 框架
- `kconfig/6.18.0`, `kconfigwidgets/6.18.0`, `kcoreaddons/6.18.0`, `kcrash/6.18.0`,
  `kdbusaddons/6.18.0`, `ki18n/6.18.0`, `kiconthemes/6.18.0.1`, `kwidgetsaddons/6.18.0`,
  `kxmlgui/6.18.0`: KF6 框架 6.18.0
- `libkdegames/26.04.0`: KDEGames6 游戏库
- `ecm/6.26.0`: KDE 6.18 基线 CMake 模块（tool_requires）
- `kiconthemes/6.18.0.1`（override=True）：消费 ohpcd 预编译包，避免本地重建
  时 ctest 失败（kpixmapsequenceloadertest 需要 shared-mime-info，OHOS 无此依赖）。

## Versions

| Version | Status |
| --- | --- |
| 26.04.0 | built |

## Notes

- 上游 enginetest（Qt Test，4 个用例）链接 KDE5 库（`KF5KDEGames`、`KF5::KDELibs4Support`），
  与 KF6 6.18 基线不兼容，无法构建；`BUILD_TESTING=OFF` 为 klickety 先例的合理处置。
- test_package 提供鸿蒙消费者验证：dlopen libQt6Core 共享库闭包加载（运行时非断言）
  + ELF `.codesign` 签名节验证 + `--version` 冒烟。
- OpenAL 运行时在 OHOS 沙箱环境缺失，CI 不运行 GUI 二进制。

Homepage: https://invent.kde.org/games/killbots
