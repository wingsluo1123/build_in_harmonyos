# launchy 2.9.1 适配笔记

## 软件身份

- **软件名**: launchy 2.9.1 —— 跨平台应用程序启动器（Qt5 Widgets + X11，索引开始菜单/文档/文件夹/书签并一键启动）
- **上游**: Slesa/launchy tag v2.9.1-pre.1（**任务头声明 URL github.com/launchy/launchy 已下线 404**；
  Arch Linux 官方打包 launchy 2.9.1 使用的权威 tag 即 v2.9.1-pre.1，sha512 与 Arch PKGBUILD
  声明值完全一致，sha256 = 26a27f4cf895cb345a277aac49b153bd3adf0ccee0d4f8716f737438bcf7c4e7）
- **类型**: Qt5 GUI 应用（TEMPLATE=app），非库；构建系统 CMake（src/CMakeLists.txt，project(LaunchyApp)）

## 编译环境

- 构建系统: cmake 4.1.2（-DCMAKE_POLICY_VERSION_MINIMUM=3.5）
- 编译日期: 2026-10-02
- 编译器: clang 15.0.4（OHOS aarch64，os=OHOS/armv8 Release）
- Profile: ohos-aarch64（cppstd17 / libc++）
- 交叉编译: CMAKE_SYSTEM_NAME=Linux（E092：CMake 无 HarmonyOS 平台模块，OHOS 基于 Linux 内核）

## 依赖（W0 检查全部已发布，R35 用 conan download 实测）

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | 含 Qt5Widgets（5.15.2 为 -no-widgets）；直接依赖避免 CMakeDeps 聚合空配置 |
| libx11 | 6.4.0 | X11/Xlib.h + libX11 |
| libxcb | 1.16 | xcb/xcb.h + libxcb（qxtglobalshortcut_x11.cpp 使用） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务头 URL github.com/launchy/launchy 404 | 上游仓库已下线 | 改用 Arch Linux 打包 launchy 2.9.1 的权威 tag Slesa/launchy v2.9.1-pre.1，sha512 与 PKGBUILD 一致核验 |
| 2 | 版本冲突 qt5-qtbase/5.15.2 vs 5.15.2.2 | qt5-qtx11extras 链上精确要求 5.15.2 | **移除 qt5-qtx11extras 依赖**（launchy 仅用 QX11Info::display()，改用 Qt5Gui QPlatformNativeInterface 获取 Display*）；qt5-qtbase 作为直接依赖 5.15.2.2 |
| 3 | CMakeDeps 只生成聚合 Qt5Config，组件 includes 为空（QTableWidget 找不到） | qt5-qtbase 以 override 进入图时组件配置降级 | 直接依赖 + 在 conanfile generate() 注入 QT5_INCLUDE_DIRS（include 根 + 全部 Qt* 模块目录 + Qt*/<version>/Qt* 私有头目录），CMakeLists 顶层 include_directories 消费 |
| 4 | 链接期 undefined QObject 符号 | override=True 时 CMakeDeps 组件 libs 为空 | 同上：qt5-qtbase 改直接依赖，组件库正常导出 |
| 5 | QSharedMemory 类型不存在 | qt5-qtbase 配方 -no-feature-sharedmemory -no-feature-systemsemaphore | singleapplication 单实例锁改用 QLockFile（QtCore，无显示环境可运行） |
| 6 | X11 宏污染 AUTOMOC 合并 TU（qdir.h Unsorted / qjsonvalue.h Bool 报 expected identifier） | X11/Xlib.h 定义 Bool/Unsorted/None/True/False 等宏；AUTOMOC 把所有 moc 并入一个 mocs_compilation.cpp TU，x11 头先引入宏再首次解析 Qt 头即炸 | x11_keytrigger.h 在引入 X11 头**之前**先完整 `#include <QtCore>/<QtGui>/<QtWidgets>`（include guard 保证之后不再重解析），X11 宏只影响本 TU X11 代码 |
| 7 | qpa/qplatformnativeinterface.h 找不到 | libqxt 依赖 Qt5Gui 私有头 | QT5_INCLUDE_DIRS 注入 include/QtGui/<version>/QtGui 私有目录 |
| 8 | 上游 CMakeLists 用 Qt5 宏（qt5_use_modules/QT5_WRAP_UI/QT5_ADD_TRANSLATION） | CMakeDeps 不导出 Qt5 模块宏；qt5-tools/linguist 未发布 | 全部改写为 CMakeDeps 可解析的 Qt5:: 目标链接 + CMAKE_AUTOMOC/AUTOUIC/AUTORCC（moc/rcc/uic 显式指向 qtbase bin/） |

## 源码修改

- patches/0001-0013：顶层/common/libqxt/launchy/plugins/specs 的 CMakeLists 平台与宏适配；
  x11_keytrigger.h/.cpp、x11_platform.cpp 的 QX11Info→QPlatformNativeInterface 替换；
  singleapplication 的 QSharedMemory→QLockFile。

## 验证结果

- W3: `conan create archives/l/launchy/2.9.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` **通过**：
  构建全部目标（launchy + common + libqxt + 插件 runner/verby/weby + launchy_specs 测试目标），
  产物 `bin/launchy` + `lib/launchy/plugins/{runner,verby,weby}.so` + skins + docs。
- test_package 消费者验证 **PASS**：bin/launchy 为 aarch64 ELF（e_machine=183），
  readelf -d DT_NEEDED 解析出 libQt5Core/Widgets/Gui/Network + libX11/libxcb + libc++_shared。
- 上游测试：launchy.specs（QtTest）在构建中经 ctest 驱动（commandlineparser + singleapplication 两套 spec），
  详细双口径台账见任务台账（第 5 项）。

## 交付物

- bin/launchy（GUI 应用可执行，R38/L0k 判定 tool 型，软件级 commands.json 已提供）
- lib/launchy/plugins/{runner,verby,weby}.so
- share/launchy/skins（Default 等皮肤）

## 注意事项

- GUI 应用需显示服务器，OHOS 无显示环境无法启动 GUI 进程（test_package 采用 ELF+DT_NEEDED 消费者验证，与 baka 先例一致）。
- 上游源码内嵌第三方组件（libqxt 全局快捷键）为静态编译进应用，无额外依赖。
---

**编译结束**: 2026-10-18 09:48
**最终状态**: built
