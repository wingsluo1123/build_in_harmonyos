# kcharselect

KDE 字符选择器（KCharSelect）：Qt6/KF6 Widgets 图形应用，把 `KCharSelect`
部件（KF6::WidgetsAddons）放进 `KXmlGuiWindow`，提供 Unicode 字符表浏览、
区块与字体切换、搜索、复制到剪贴板，以及 KDE 书签菜单（KF6::Bookmarks）、
配色方案菜单（KColorSchemeMenu）与崩溃处理（KF6::Crash）。
安装 `bin/kcharselect`、`.desktop` 与 appdata 元数据。

- 上游：https://invent.kde.org/utilities/kcharselect
- 适配版本：26.04.0（archives/k/kcharselect/26.04.0/）
- 依赖：qtbase/6.11.1 + KF6 6.18.0 闭包（Bookmarks/CoreAddons/Crash/I18n/
  WidgetsAddons/XmlGui/ConfigWidgets/IconThemes 及其运行时传递依赖）+ `tool_requires ecm/6.26.0`

## 上游测试

kcharselect 26.04.0 **无任何上游测试**（0 用例）：tarball 内无 `autotests/`、
无 `tests/` 目录（顶层仅 `doc/`、`pics/`、`po/`、`LICENSES/`），`CMakeLists.txt`
仅注册可执行目标 `kcharselect`（`add_executable` + `target_sources`）且未注册任何
测试（无 `add_test`/`enable_testing`/`ecm_add_test`；仅有的两处 `BUILD_TESTING`
在 `CMakePresets.json` 与 `snapcraft.yaml`，都只是传 `-DBUILD_TESTING=OFF`）；
上游 CI 的 `.gitlab-ci.yml` 引入构建/打包/lint 模板，但这些模板仅在项目注册了
测试时才执行 ctest，本项目未注册；`.kde-ci.yml` 也未声明测试目标。清点证据与
消费者用例详见 `26.04.0/test_package/MANIFEST.yml`。

## OHOS 适配要点（无源码补丁）

`KF_IGNORE_PLATFORM_CHECK=TRUE`、`KF_SKIP_PO_PROCESSING=ON`、`BUILD_TESTING=OFF`；
`KF6DocTools` 为上游可选依赖，不提供时 `doc/` 与 `kdoctools_install(po)` 自动
配置掉；手工补 `ECM_MODULE_PATH` 与 `conan_cmakedeps_paths.cmake`；
`-Wl,-z,max-page-size=0x1000`；`package()` 内 DT_NEEDED 净化为 basename 并重签名。

运行期依赖库（Qt6/KF6）由包的 `package_info()` 通过 `runenv_info` 导出
`LD_LIBRARY_PATH`/`QT_PLUGIN_PATH` 解析：实测产物 `.dynamic` 中**没有**
DT_RPATH/DT_RUNPATH 条目（配方虽设置了 `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH`，
但 CMake 只在链接期已产出 RPATH 时才做安装期改写），因此使用方需经
`conan install` 生成的 runenv 环境运行。

## 许可

上游 `COPYING` / `LICENSES/GPL-2.0-or-later.txt` / `org.kde.kcharselect.appdata.xml`
（`<project_license>GPL-2.0+`）均为 **GPL-2.0-or-later**（Conan `license` 字段据此
填写）；运行时 `--license` 输出 `This program is distributed under the terms of the
GPL v2.` + GNU GPL v2 全文，与 SPDX 声明一致。
