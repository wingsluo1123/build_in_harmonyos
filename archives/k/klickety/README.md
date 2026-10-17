# klickety

KDE SameGame/Clickomania 适配——颜色消除类益智游戏（Qt6/KF6 QGraphics 应用，基于 KDEGames6）。

## OHOS adaptation

- Builds the KDE release tarball with CMake on HarmonyOS PC (aarch64).
- Removes KIO dependency (`kio/6.14.0` 与 KF6 6.18 闭包冲突) 和 DocTools (handbook 非运行时必需).
- 用 libkdegames/26.04.0.1 避免 kconfig 版本冲突.
- ECM_MODULE_PATH 手动设置 (cmake_find_mode=none).
- Patches:
  - `0001-cmake.patch`: 移除 KIO、DocTools、doc/ 子目录
  - `0002-src-cmake.patch`: 移除 KF6::KIOWidgets 链接，添加 KF6::CoreAddons
  - `0003-src-ui.patch`: KUrlRequester 替换为 QLineEdit (避免 KIOWidgets 头文件依赖)

## Dependencies

- `qtbase/6.11.1` + `qtsvg/6.11.1`: Qt6 基础
- `karchive/6.18.0` (override): KF6 框架
- `kconfig/6.18.0`, `kconfigwidgets/6.18.0`, `kcoreaddons/6.18.0`, `kcrash/6.18.0`, `kdbusaddons/6.18.0`, `ki18n/6.18.0`, `kiconthemes/6.18.0`, `kwidgetsaddons/6.18.0`, `kxmlgui/6.18.0`: KF6 框架 6.18.0
- `libkdegames/26.04.0.1`: KDEGames6 游戏库

## Notes

- 上游无测试套件 (N=0)，test_package 提供运行时 smoke test.
- OpenAL 运行时缺失 (OHOS 沙箱环境)，CI 不运行 GUI 二进制.
- kiconthemes registry 缓存有相对 DT_NEEDED (`../../bin/libKF6IconThemes.so`)，需手动创建 bin/ 文件夹兼容层.

## References

- https://invent.kde.org/games/klickety
- https://community.kde.org/Games/Klickety
