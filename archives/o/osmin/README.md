# osmin

GNU/Linux 与 OpenHarmony PC 上的离线 GPS 导航应用（C++/Qt6 + libosmscout）。

- **上游**：<https://github.com/janbar/osmin>（GPL-3.0）
- **构建系统**：CMake（>= 3.20，C++20）
- **主要依赖**：Qt6（Core/Gui/Qml/Widgets/Svg/Network/Quick/Multimedia/Positioning/Sensors/RemoteObjects/Core5Compat）、libxml2、zlib
- **地图后端**：libosmscout（osmin 以 git submodule 内嵌于 `backend/libosmscout/`，本配方以 tarball 源码内联适配，不作为 conan 依赖）
- **产物**：`bin/osmin`（QML 桌面导航程序；`-service` 为其无头服务运行模式，非独立可执行文件）、`share/applications/osmin.desktop` 桌面入口、`share/osmin/resources/**`（随包安装的 QML/资源文件）

## 适配说明（OpenHarmony PC / aarch64）

| 问题 | 处理 |
|------|------|
| OHOS libc++ 15.0.4 下 `__cpp_lib_ranges` 未定义（C++20 `std::views`/`std::ranges` 报错） | 配方注入 `-D_LIBCPP_ENABLE_EXPERIMENTAL` |
| `CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake **不定义 `UNIX`** → `src/signalhandler.cpp` 被静默丢弃、链接期 `SignalHandler::*` 未定义 | 配方注入 `UNIX=ON` |
| OHOS qtbase 未构建 QtOpenGL（`qtgui-config.h: QT_NO_OPENGL 1`）→ libosmscout-client-qt `TiledMapRenderer.cpp` 编译失败 | `patches/0001-libosmscout-client-qt-guard-no-opengl.patch`（知识库条目 KB-NO-OPENGL） |
| 构建期 Qt 工具 `repc` 无 RPATH，加载不到 `libQt6Core.so.6` | `build()` 内自建 `Environment` 追加 `LD_LIBRARY_PATH` |
| 上游内置 zlib `ExternalProject` 兜底在离线/受限环境不稳定 | zlib 声明为常规 `requires` + `generate()` 注入 `ZLIB_ROOT`/`ZLIB_LIBRARY`/`ZLIB_INCLUDE_DIR` |
| 上游无测试用例（无 `add_test`/`enable_testing`/QtTest 引用） | 适配后补全鸿蒙独有测试：`test_package/` 走 `-service` 无头模式做产物级断言 |

详细适配过程见 [`1.15.1/notes.md`](1.15.1/notes.md)；验证方式为 `conan create`（L1 test_package 走 `-service` 无头模式断言产物与 `$HOME/osmin`、GPX 目录），CI 门禁脚本为 `ci/conan/build_and_test.sh`。
