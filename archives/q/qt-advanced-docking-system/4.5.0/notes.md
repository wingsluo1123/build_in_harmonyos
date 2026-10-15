# qt-advanced-docking-system 4.5.0 适配笔记

## 软件信息

| 项 | 值 |
|----|----|
| 上游 | Uwe Kindler, Qt Advanced Docking System (QtADS) |
| 版本 | 4.5.0（GitHub release tag） |
| 许可 | LGPL-2.1-only |
| 类型 | Qt6 Widgets C++ 库（停靠窗口/浮动容器/自动隐藏侧栏/视角） |
| 上游仓库 | https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System |

## 编译环境

- 构建系统: cmake（上游顶层 CMakeLists.txt，project(QtADS LANGUAGES CXX)）
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/clang++`，aarch64-linux-ohos）
- 目标: os=OHOS os.version=6.0 arch=armv8 compiler=clang libc++
- 状态: published

## 语言预检（R47）

`lang-preflight` 工具输出 `detected_language=mixed`（顶层 `pyproject.toml` 命中
python 打包 manifest，源码统计 cpp 78%）。按 R47 附录 D.4 边界规则核验主库主体后
判定为 **cpp**：

- 库本体 `src/`：23 个 `.cpp` + 24 个 `.h`（100% C/C++），上游唯一构建目标
  `qtadvanceddocking-qt6` 即在此目录；
- 全部 15 个 `.py` 均为可选绑定/示例辅助（`pyproject.toml` 是 PyQt5/sip 绑定元数据
  `PyQtAds`，`sip/*.sip` 24 个接口定义，`project.py` 绑定构建脚本，`demo/`、`examples/`
  下的启动脚本）；
- 依据知识库既有条目
  `knowledge/DRAFT-cmsis-dsp-1.18.0-lang-preflight-pyproject-python-misdetect.kv`
  （`rec_impl = agent-boundary-rule-override`）：主库主体为 C/C++ 时按 D.4 判
  c/cpp 并继续适配。

完整证据（工具原始输出 + 文件计数 + 辅助文件定位）见
[`reports/lang_preflight.log`](reports/lang_preflight.log)。

## 编译步骤

```bash
conan create archives/q/qt-advanced-docking-system/4.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="qt-advanced-docking-system/*"
```

配方 `generate()` 注入的 CMake 参数：

| 参数 | 值 | 原因 |
|------|----|------|
| `BUILD_STATIC` | `OFF` | 上游用 `BUILD_STATIC` 区分静态/动态（不是 `BUILD_SHARED_LIBS`） |
| `BUILD_EXAMPLES` | `OFF` | `examples/`、`demo/` 是 GUI 程序，非库本体 |
| `ADS_VERSION`（`cli_args` -D） | `4.5.0` | tarball 无 `.git`，否则走 `git describe` |
| `CMAKE_MODULE_PATH` | `<src>/cmake/modules` | 上游只在 git 分支里设置，`src/CMakeLists.txt` 无条件 `include(Versioning)` |
| `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` | `-Wl,-soname,` | OHOS 无 `Platform/HarmonyOS.cmake`，否则 `.so` 无 DT_SONAME（E383） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `project()` 报 `VERSION "HEAD-HASH-NOTFOUND.HEAD-HASH-NOTFOUND.HEAD-HASH-NOTFOUND" format invalid` | CMake 到**第一个 `project()`** 才加载 `CMAKE_TOOLCHAIN_FILE`，而上游在 `project()` **之前**读 `ADS_VERSION`，`tc.variables` 此时不可见 | 改用 `cmake.configure(cli_args=["-DADS_VERSION=4.5.0"])`（命令行 cache 项在配置开始前即生效） |
| 2 | `include(Versioning)` 找不到模块 | 上游只在 `if(NOT ADS_VERSION)` 分支设置 `CMAKE_MODULE_PATH=<src>/cmake/modules`，而 `src/CMakeLists.txt` 无条件 `include(Versioning)` | 配方用 `tc.variables["CMAKE_MODULE_PATH"]` 显式补上 |
| 3 | `fatal error: 'xcb/xcb.h' file not found` | CMake 对 `CMAKE_SYSTEM_NAME=HarmonyOS` **不置 `UNIX`**（无 `Platform/HarmonyOS.cmake`，提示 "System is unknown to cmake"），上游 5 处 `if(UNIX AND NOT APPLE)` 全部落空；而 Qt 的 `Q_OS_UNIX` 在 OHOS 上是定义的，源码仍会 include xcb/GuiPrivate 私有头 | 按知识条目 **E532**（`harmonyos-into-unix-branch`）惯例把 5 处条件扩展为 `(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") AND NOT APPLE` |
| 4 | 消费者链接报 `undefined reference ... ads::CFloatingWidgetTitleBar::*` | 第 3 条中遗漏了第 5 处 `if (UNIX AND NOT APPLE)`——它负责把 `linux/FloatingWidgetTitleBar.cpp` 加入源码列表；缺它时 `.so` 带未定义符号，直到消费者以 `--no-allow-shlib-undefined` 链接才暴露 | 同一补丁内一并扩展该条件 |
| 5 | `find_package(libxcb)` 失败 / `xcb/xcb.h` 仍找不到 | 上游裸链库名 `xcb`；且配方未声明 `CMakeDeps`，libxcb 的 CMake 配置根本没生成 | 补丁改为 `find_package(libxcb REQUIRED)` + `libxcb::xcb`；配方 `generate()` 增加 `CMakeDeps(self).generate()` |
| 6 | 自写 `conan_cmakedeps_paths.cmake` 后 `find_package(libxcb)` 仍失败 | 该文件存在时 CMakeToolchain 会**跳过**自身的 `find_paths` 块，导致生成器目录不再加入 `CMAKE_PREFIX_PATH`/`CMAKE_MODULE_PATH` | 自写文件里同时 `list(PREPEND ... "${CMAKE_CURRENT_LIST_DIR}")`（= 生成器目录） |
| 7 | test_package `find_package(qtadvanceddocking-qt6)` 报找不到 `qtbase` 配置 | qtbase 设 `cmake_find_mode=none` 且无 `cmake_file_name`/`cmake_target_name`，CMakeDeps 仍会生成 `find_dependency(qtbase)` 与不存在的 `qtbase::qtbase` | 消费者侧 `CMakeDeps.set_property("qtbase", "cmake_file_name", "Qt6")` + `cmake_target_name = "Qt6::Widgets"`（libfm-qt / pcmanfm-qt 同款做法），并先 `find_package(Qt6)` 使 `if(NOT Qt6_FOUND)` 短路 |
| 8 | 消费者编译仍缺 `xcb/xcb.h` | libxcb 是**传递依赖**，默认不传播头文件/库，而本库**公共头** `ads_globals.h` 在 `Q_OS_UNIX` 下 include `<xcb/xcb.h>` | 依赖声明改为 `self.requires("libxcb/1.17.0.1", transitive_headers=True, transitive_libs=True)` |
| 9 | 打包 `.so` 无 `DT_SONAME`（CI L5a 拒绝） | 无 `Platform/HarmonyOS.cmake` 时 `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 为空，上游 `VERSION/SOVERSION` 不生效（E383） | 配方注入 `-Wl,-soname,`，产物恢复 `libqtadvanceddocking-qt6.so.4` 与 `.so.4.5.0` 符号链接 |

## 源码修改

单补丁 `patches/0001-src-CMakeLists.txt.patch`（+7/-6，仅 `src/CMakeLists.txt`）：

1. **HarmonyOS 归入 UNIX 分支**（E532 惯例，5 处）：
   `if (UNIX AND NOT APPLE ...)` → `if ((UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") AND NOT APPLE ...)`，
   覆盖：`ads_DEP_LIBS` 加 `GuiPrivate` 组件、`include_directories(Qt6Gui_PRIVATE_INCLUDE_DIRS)`、
   `target_link_libraries(... Qt6::GuiPrivate)`、`set(ads_SRCS linux/FloatingWidgetTitleBar.cpp ...)`、
   xcb 链接分支。
2. **xcb 目标可解析**：`target_link_libraries(... PUBLIC xcb)` →
   `find_package(libxcb REQUIRED)` + `target_link_libraries(... PUBLIC libxcb::xcb)`。

补丁不含任何平台宏（无 `__OHOS__`），未改动上游源码逻辑，仅平台判定与包目标名。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1 | Qt6 Core/Gui/Widgets + `Qt6::GuiPrivate`（`qpa/qplatformnativeinterface.h`）；OHOS 已发布二进制 |
| libxcb | 1.17.0.1 | 源码 `Q_OS_UNIX` 下无条件 include `<xcb/xcb.h>`；仓库当前代际（lemonbar/libfm-qt/libx11 同版本） |

依赖预检（W0）：`bash ci/scripts/preflight_check.sh qt-advanced-docking-system/4.5.0 --deps "qtbase/6.11.1 libxcb/1.17.0.1"` 全部已发布（R35 口径用 `conan download` / `conan install` 实测，不用 `conan list`）；
`conan install` 实测 qtbase/6.11.1 二进制可下载（20.3MB），libxcb/1.17.0.1 解析为 Cache（1.17.0 亦可用，最终取仓库当前代际 1.17.0.1，与 lemonbar/libfm-qt/libx11 一致）。

## 验证结果

```bash
conan create archives/q/qt-advanced-docking-system/4.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="qt-advanced-docking-system/*"
# → EXIT=0，test_package: 30 checks, 0 failures, RESULT: PASSED
```

`test_package` 在 `QT_QPA_PLATFORM=offscreen` 下真实驱动公共 API（R34）：配置标志、
`CDockManager` 生命周期与 `dockWidgetsMap()` 注册表、四个停靠区建区、tab 化停靠、
`toggleView()` 关闭/重开、视角（`addPerspective`/`perspectiveNames`）、
`saveState`/`restoreState` 往返、`CFloatingDockContainer` 浮动与回停。

SONAME 自查（CI L5）：DT_SONAME = `libqtadvanceddocking-qt6.so.4`（相对路径）；
DT_NEEDED 全为裸名；包内 `.cmake` 无 `IMPORTED_NO_SONAME TRUE`。

详见 [`reports/test-report.md`](reports/test-report.md)。

## 上游测试

上游 4.5.0 **不带任何自动化测试套件**（无 `tests/` 目录，无 QtTest/ctest/gtest 命中，
`CMakeLists.txt` 无 `enable_testing`/`add_test`，`.github/workflows/` 仅构建）。
清点证据与结论见 [`test_package/MANIFEST.yml`](test_package/MANIFEST.yml)。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libqtadvanceddocking-qt6.so.4.5.0` | 库本体（含 `.so`、`.so.4` 符号链接） |
| `include/qtadvanceddocking-qt6/*.h` | 公共头 24 个 |
| `lib/cmake/qtadvanceddocking-qt6/*.cmake` | 上游导出的 CMake 包（`ads::qtadvanceddocking-qt6`） |
| `licenses/`、`share/ads/license/` | LGPL-2.1 许可 |

## 注意事项

1. **下游消费**：本库公共头 include Qt 头与 `<xcb/xcb.h>`，而 qtbase 为
   `cmake_find_mode=none`（CMakeDeps 无法为其生成目标）。下游配方需：
   - 把 qtbase 包的 `lib/cmake` 加入 `CMAKE_PREFIX_PATH`（或设 `Qt6_DIR`）并自行
     `find_package(Qt6 COMPONENTS Core Gui Widgets)`；
   - 对 qtbase 设 `CMakeDeps.set_property("qtbase", "cmake_file_name", "Qt6")`
     与 `cmake_target_name = "Qt6::Widgets"`，避免生成悬空的
     `find_dependency(qtbase)` / `qtbase::qtbase`。
   参考 `test_package/conanfile.py`。
2. **OHOS 无 X11**：`_NET_WM_STATE` 等 X11 窗口提示代码在 OHOS 上编译但运行时不会
   执行（`QGuiApplication::platformName() == "xcb"` 恒为假），libxcb 仅作为编译/链接
   依赖存在。
3. **版本来源**：升级上游版本时须同步更新 `ADS_VERSION`（`cli_args`），不可依赖
   tarball 内的 git 信息。
4. **提交前务必还原 conandata.yml 源 URL**：W3 本地 CI 模拟
   （`ci/conan/build_and_test.sh`）会把 `sources.url` 原地改写成
   `[gh-proxy.com 镜像, 官方源]` 列表**且不还原**。R39/PF7 要求 conandata 只写上游
   官方源（镜像回退由 CI 自动处理），仓库中 757 个历史归档的镜像 URL 是遗留状态，
   不可照抄。本归档已还原为仅官方源。
5. **源码 URL 采用 GitHub 官方 codeload 端点**（`codeload.github.com/.../tar.gz/refs/tags/4.5.0`）：
   - `github.com/.../archive/...` 本身就是 302 重定向到 codeload，故二者**同为官方源**；
   - 实测 codeload 直连 HTTP 200 且完整下载 22295385 字节，产物 sha256 与 archive
     形式**逐字节相同**（`a438810b…1f09`，已校验）；
   - CI 的 `get_mirrors()` 只对 `^https?://github\.com/` 注入 `gh-proxy.com` 镜像，而该
     镜像当前对本环境返回 **403「Access to this resource is forbidden」**，导致
     `github.com` 形式的源码在 CI 上必然下载失败（#92477 实测：镜像 403 → github.com
     连接超时）。codeload 形式不被该正则匹配，conan 直连即可成功；
   - 另注：CI 的 pre-download 步骤用 Python `subprocess` 调 `curl`，而 worker 的 PATH
     （`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:…/.local/bin`）不含
     `usr/local/bin`，故该步骤恒报 `[Errno 2] No such file or directory: 'curl'`，
     属 worker 环境问题（已写入 SKILL_FEEDBACK）。
---

**编译结束**: 2026-10-15 01:19
**最终状态**: published
