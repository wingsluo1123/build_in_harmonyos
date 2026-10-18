# PreviSat

开源卫星跟踪软件（Astropedia），HarmonyOS PC（OHOS aarch64）适配归档。

- 官网：<http://previsat.free.fr/> （上游站点：<http://astropedia.free.fr>）
- 上游版本：7.2.1.3（Qt6 / CMake / C++20 桌面应用）
- 适配版本目录：[`7.2.1.3/`](7.2.1.3/)（`conanfile.py`、`conandata.yml`、`patches/`、`test_package/`、`notes.md`）
- 产品形态：可执行程序 `bin/PreviSat` + 运行期数据 `bin/data`（satellites.db、声音提示、配置/星空/边界等）+ `bin/translations`，可重定位（`PORTABLE_BUILD=1`）
- 依赖：`qtbase-sql-dbus/6.11.1`（Qt6 Core/Gui/Widgets/Network/Xml/Concurrent/Sql）、`qtmultimedia/6.11.1`（声音提示）
- 已知限制：鸿蒙 PC 无窗口系统，需以 `QT_QPA_PLATFORM=offscreen`（或后续平台插件）无头运行；上游 7.2.1.3 发布包不含测试套件，故以 `test_package/` 的运行时行为测试替代
